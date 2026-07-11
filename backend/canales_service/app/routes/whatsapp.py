"""WhatsApp routes for channel delivery and webhook handling.

Webhook flow (with Cloud Tasks enabled via USE_CLOUD_TASKS=true):
  1. Evolution API  ──POST /webhook/whatsapp──▶  canales_service
  2. canales_service validates token, parses payload
  3. canales_service enqueues Cloud Task → responds 200 immediately
  4. Cloud Tasks     ──POST /process-webhook──▶  tasks service
  5. tasks service   ──POST /webhook/whatsapp/process──▶  canales_service
  6. canales_service runs full pipeline (classify → AI → reply)

When USE_CLOUD_TASKS=false (default): step 6 runs synchronously in step 2.
"""

import hmac
import logging
import time
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.whatsapp import (
    InstanceSettingsRequest,
    InstanceSettingsResponse,
    WhatsAppHistorySyncRequest,
    WhatsAppHistorySyncResponse,
    WhatsAppIncoming,
    WhatsAppOutboundRequest,
    WhatsAppOutgoing,
    WhatsAppReplyRequest,
    WhatsAppReplyResponse,
    WhatsAppResponse,
)
from app.services.media_service import detect_media_from_payload, send_media_via_evolution
from app.services import instance_service, qr_service, whatsapp_service
from shared.database.dependencies import get_db
from shared.database.session import set_instance_lookup_context, set_tenant_context
from shared.middleware import get_current_user, require_user_or_service
from shared.models.enums import UserRole
from shared.utils.service_access import WEBHOOK_PROCESSORS, WHATSAPP_SENDERS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["whatsapp"])

_cloud_tasks_client = None  # lazy singleton

# Dedup cache: message_id → timestamp. Prevents duplicate processing
# when Evolution API global webhook fires multiple times per message.
_SEEN_MESSAGE_IDS: dict[str, float] = {}
_DEDUP_TTL_SECONDS = 60
_DEDUP_MAX_SIZE = 5000


def _is_duplicate_message(message_id: str) -> bool:
    """Return True if this message_id was already seen within the TTL window."""
    now = time.monotonic()
    # Evict expired entries periodically
    if len(_SEEN_MESSAGE_IDS) > _DEDUP_MAX_SIZE:
        expired = [k for k, ts in _SEEN_MESSAGE_IDS.items() if now - ts > _DEDUP_TTL_SECONDS]
        for k in expired:
            del _SEEN_MESSAGE_IDS[k]
    if message_id in _SEEN_MESSAGE_IDS:
        if now - _SEEN_MESSAGE_IDS[message_id] < _DEDUP_TTL_SECONDS:
            return True
    _SEEN_MESSAGE_IDS[message_id] = now
    return False
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentActor = Annotated[
    dict,
    Depends(
        require_user_or_service(
            UserRole.ADMIN,
            UserRole.ASESOR,
            UserRole.VIEWER,
            service_scopes=("whatsapp:send",),
            service_callers=WHATSAPP_SENDERS,
        )
    ),
]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/webhook/whatsapp", status_code=status.HTTP_200_OK)
@router.post(
    "/webhook/whatsapp/{event_type}",
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
async def webhook_whatsapp(request: Request, event_type: str | None = None) -> dict:
    """Receive incoming WhatsApp messages from Evolution API."""
    del event_type
    _validate_webhook_token(request)
    payload = await request.json()

    event = payload.get("event", "unknown")
    raw_data = payload.get("data")

    # ── Comprehensive poll vote detection ──────────────────────────
    # Log every webhook so we can trace poll vote payloads
    _data_summary = "none"
    if isinstance(raw_data, dict):
        _data_summary = str(sorted(raw_data.keys()))
    elif isinstance(raw_data, list):
        _data_summary = f"list[{len(raw_data)}]"
        if raw_data and isinstance(raw_data[0], dict):
            _data_summary += f" first_keys={sorted(raw_data[0].keys())}"
    logger.info("Webhook: event=%s data=%s", event, _data_summary)

    if _is_connection_update(payload):
        return await _handle_connection_update(payload, request)

    # ── Poll vote extraction ──────────────────────────────────────
    # Poll votes can arrive in many Evolution API payload shapes.
    # We search exhaustively for pollUpdates at any nesting level.
    poll_updates = _find_poll_updates(payload)
    if poll_updates:
        vote_text = _extract_poll_vote_text(poll_updates)
        voter_jid = _find_poll_voter(payload, poll_updates)
        if vote_text and voter_jid:
            # Dedup key = (voter, ORIGINAL poll message id). WhatsApp emits
            # a new vote-message for every click (including vote changes),
            # so using the vote's own id lets repeat clicks re-trigger the
            # agent. Keying on the original poll id means: the first vote on
            # a given poll processes; any subsequent click on the same poll
            # within the TTL window is dropped.
            original_poll_id = ""
            if isinstance(poll_updates, list) and poll_updates:
                first_update = poll_updates[0] if isinstance(poll_updates[0], dict) else {}
                pmk = first_update.get("pollUpdateMessageKey") or {}
                if isinstance(pmk, dict):
                    original_poll_id = pmk.get("id", "") or ""
            vote_msg_id = ""
            if isinstance(raw_data, dict):
                poll_key = raw_data.get("key", {})
                if isinstance(poll_key, dict):
                    vote_msg_id = poll_key.get("id", "") or ""
            # Without the original poll id we cannot tell two clicks on the
            # same poll apart by message id (each click gets a fresh id), so
            # fall back to voter-level dedup within the TTL window.
            dedup_key = (
                f"poll:{voter_jid}:{original_poll_id}"
                if original_poll_id
                else f"poll:{voter_jid}"
            )
            if dedup_key and _is_duplicate_message(dedup_key):
                logger.info(
                    "Duplicate vote on poll %s from %s ignored (vote_msg=%s)",
                    original_poll_id or "?", voter_jid, vote_msg_id,
                )
                return {"status": "duplicate_vote"}

            instance_name = payload.get("instance", "")
            logger.info(
                "Poll vote processed: voter=%s vote='%s' poll_id=%s vote_msg=%s",
                voter_jid, vote_text, original_poll_id or "?", vote_msg_id,
            )
            incoming_data = {
                "sender": voter_jid,
                "message": vote_text,
                "instance_name": instance_name,
                "from_me": False,
            }
            return await _process_message_webhook(incoming_data, request)
        logger.warning("Poll updates found but could not extract vote/voter: vote=%r voter=%r", vote_text, voter_jid)

    # Skip non-message events (status updates, chats.upsert, etc.)
    if isinstance(raw_data, list):
        logger.debug("Array-data event=%s with no poll — ignoring", event)
        return {"status": "ignored", "reason": "array_event"}

    if not isinstance(raw_data, dict):
        raw_data = {}

    incoming = _parse_evolution_payload(payload)
    if incoming is None:
        return {"status": "ignored"}

    # ── Group message routing (driver claim via WhatsApp group) ────
    if isinstance(raw_data, dict) and raw_data.get("_is_group"):
        return await _handle_group_message(raw_data, incoming, request)

    incoming_data = incoming.model_dump()
    # Pass the raw message_id from Evolution for media download
    raw_key = raw_data.get("key", {}) if isinstance(raw_data, dict) else {}
    message_id = raw_key.get("id", "") if isinstance(raw_key, dict) else ""
    if message_id:
        incoming_data["external_wa_id"] = message_id
        if _is_duplicate_message(message_id):
            logger.debug("Duplicate webhook ignored: message_id=%s", message_id)
            return {"status": "duplicate"}

    settings = request.app.state.settings
    if settings.USE_CLOUD_TASKS:
        return await _enqueue_webhook_task(incoming_data, request)

    return await _process_message_webhook(incoming_data, request)


@router.post("/whatsapp/send", response_model=WhatsAppResponse)
async def send_whatsapp(
    body: WhatsAppOutgoing,
    request: Request,
    current_user: CurrentActor = None,
    db: DbSession = None,
) -> WhatsAppResponse:
    """Send a WhatsApp message (text or media) through Evolution API."""
    _ensure_tenant_access(body.tenant_id, current_user)
    instance = await _get_instance_or_404(db, body.tenant_id)
    settings = request.app.state.settings

    try:
        if body.media_url and body.media_type:
            result = await send_media_via_evolution(
                to=body.to,
                media_url=body.media_url,
                media_type=body.media_type,
                instance_name=instance.instance_name,
                settings=settings,
                file_name=body.file_name,
                caption=body.caption or body.message,
                mimetype=body.mimetype,
            )
        else:
            result = await whatsapp_service.send_message(
                to=body.to,
                message=body.message or "",
                instance_name=instance.instance_name,
                settings=settings,
            )
    except (httpx.HTTPError, RuntimeError, SQLAlchemyError) as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", body.to, exc)
        return WhatsAppResponse(success=False, message_id=None)

    message_id = result.get("key", {}).get("id")
    return WhatsAppResponse(success=True, message_id=message_id)


@router.post("/whatsapp/reply", response_model=WhatsAppReplyResponse)
async def reply_to_prospect(
    body: WhatsAppReplyRequest,
    request: Request,
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> WhatsAppReplyResponse:
    """Send a human agent reply to a prospect via WhatsApp and persist it."""
    tenant_id = current_user.get("tenant_id")
    instance = await _get_instance_or_404(db, tenant_id)
    settings = request.app.state.settings

    try:
        result = await whatsapp_service.send_human_reply(
            lead_id=body.lead_id,
            message=body.message,
            tenant_id=tenant_id,
            instance_name=instance.instance_name,
            settings=settings,
            media_url=body.media_url,
            media_type=body.media_type,
            file_name=body.file_name,
            caption=body.caption,
            mimetype=body.mimetype,
        )
    except (httpx.HTTPError, RuntimeError, SQLAlchemyError) as exc:
        logger.error("Failed to send human reply to lead %s: %s", body.lead_id, exc)
        return WhatsAppReplyResponse(success=False, message_id=None, lead_id=body.lead_id)

    return WhatsAppReplyResponse(
        success=True,
        message_id=result.get("message_id"),
        lead_id=body.lead_id,
    )


@router.post("/whatsapp/send-outbound", response_model=WhatsAppReplyResponse)
async def send_outbound_message(
    body: WhatsAppOutboundRequest,
    request: Request,
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> WhatsAppReplyResponse:
    """Send an outbound WhatsApp message to a lead.

    If ``use_ai`` is True, the message is passed as context to the AI to
    generate the actual text sent.  Otherwise the human-written message
    is sent directly.  The message is always persisted in conversation
    history.
    """
    tenant_id = current_user.get("tenant_id")
    lead_id = UUID(body.lead_id)
    instance = await _get_instance_or_404(db, tenant_id)
    settings = request.app.state.settings

    try:
        result = await whatsapp_service.send_outbound(
            lead_id=lead_id,
            message=body.message,
            use_ai=body.use_ai,
            tenant_id=tenant_id,
            instance_name=instance.instance_name,
            settings=settings,
            media_url=body.media_url,
            media_type=body.media_type,
            file_name=body.file_name,
            caption=body.caption,
            mimetype=body.mimetype,
        )
    except (httpx.HTTPError, RuntimeError, SQLAlchemyError) as exc:
        logger.error("Failed to send outbound message to lead %s: %s", body.lead_id, exc)
        return WhatsAppReplyResponse(success=False, message_id=None, lead_id=lead_id)

    return WhatsAppReplyResponse(
        success=True,
        message_id=result.get("message_id"),
        lead_id=lead_id,
    )


@router.post(
    "/whatsapp/instance/{tenant_id}/settings",
    response_model=InstanceSettingsResponse,
)
async def configure_instance(
    tenant_id: UUID,
    body: InstanceSettingsRequest,
    request: Request,
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> InstanceSettingsResponse:
    """Apply anti-ban settings to a WhatsApp instance."""
    _ensure_tenant_access(tenant_id, current_user)
    instance = await _get_instance_or_404(db, tenant_id)
    settings = request.app.state.settings

    try:
        await qr_service.configure_instance_settings(
            instance_name=instance.instance_name,
            reject_call=body.reject_call,
            always_online=body.always_online,
            read_messages=body.read_messages,
            settings=settings,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        raise _settings_error(instance.instance_name) from exc

    return InstanceSettingsResponse(success=True, instance_name=instance.instance_name)


@router.post(
    "/whatsapp/instance/{tenant_id}/history/sync",
    response_model=WhatsAppHistorySyncResponse,
)
async def sync_instance_history(
    tenant_id: UUID,
    request: Request,
    body: WhatsAppHistorySyncRequest | None = None,
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> WhatsAppHistorySyncResponse:
    """Backfill existing WhatsApp chats from Evolution into Prospectos history."""
    _ensure_tenant_access(tenant_id, current_user)
    instance = await _get_instance_or_404(db, tenant_id)
    settings = request.app.state.settings
    sync_request = body or WhatsAppHistorySyncRequest()

    try:
        result = await whatsapp_service.sync_historical_conversations(
            instance_name=instance.instance_name,
            tenant_id=instance.tenant_id,
            settings=settings,
            page_size=sync_request.page_size,
            max_chats=sync_request.max_chats,
            since=sync_request.since,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        logger.exception("Failed historical WhatsApp sync for %s", instance.instance_name)
        raise _history_sync_error(instance.instance_name) from exc

    return WhatsAppHistorySyncResponse(
        success=result["chats_failed"] == 0,
        instance_name=instance.instance_name,
        chats_scanned=result["chats_scanned"],
        chats_imported=result["chats_imported"],
        chats_failed=result["chats_failed"],
        messages_imported=result["messages_imported"],
        messages_skipped=result["messages_skipped"],
    )


@router.get("/webhook/meta", status_code=status.HTTP_200_OK)
async def meta_webhook_verify(request: Request):
    """Meta webhook verification challenge (GET request from Meta during setup).

    Meta sends: hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
    We must return the challenge value if the verify_token matches.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    settings = request.app.state.settings
    expected_token = settings.WA_BUSINESS_TOKEN_WEBHOOK

    if mode == "subscribe" and token and expected_token and hmac.compare_digest(token, expected_token):
        logger.info("Meta webhook verification successful")
        return int(challenge) if challenge else ""

    logger.warning("Meta webhook verification failed: mode=%s", mode)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


def _validate_webhook_token(request: Request) -> None:
    """Validate that webhook requests carry the configured shared secret."""
    settings = request.app.state.settings
    token = settings.WEBHOOK_TOKEN.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook token is not configured",
        )
    incoming = request.headers.get("apikey", "") or request.query_params.get("token", "")
    if not incoming or not hmac.compare_digest(incoming, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token",
        )


def _ensure_tenant_access(tenant_id: UUID, current_user: dict) -> None:
    if tenant_id == current_user.get("tenant_id"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cannot manage instances for another tenant",
    )


async def _get_instance_or_404(db: AsyncSession, tenant_id: UUID):
    instance = await instance_service.get_instance_for_tenant(db, tenant_id)
    if instance is not None:
        return instance
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No WhatsApp instance registered for this tenant",
    )


@router.post(
    "/webhook/whatsapp/process",
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
async def process_webhook_internal(
    request: Request,
    current_actor: Annotated[
        dict,
        Depends(
            require_user_or_service(
                service_scopes=("webhook:process",),
                service_callers=WEBHOOK_PROCESSORS,
            )
        ),
    ] = None,
) -> dict:
    """Internal endpoint called by tasks service to process an enqueued webhook.

    Authenticated via internal service JWT (tasks → canales_service).
    """
    data = await request.json()
    return await _process_message_webhook(data, request)


async def _enqueue_webhook_task(data: dict, request: Request) -> dict:
    """Enqueue webhook processing to Cloud Tasks and return immediately."""
    global _cloud_tasks_client
    if _cloud_tasks_client is None:
        from shared.utils.cloud_tasks import CloudTasksClient
        _cloud_tasks_client = CloudTasksClient()

    settings = request.app.state.settings
    tasks_url = f"{settings.SERVICE_TASKS_URL}/api/v1/tasks/process-webhook"
    request_id = request.headers.get("x-request-id", "")

    try:
        task_name = await _cloud_tasks_client.enqueue(
            url=tasks_url,
            payload=data,
            headers={"X-Request-ID": request_id} if request_id else None,
        )
        logger.info(
            "Webhook enqueued to Cloud Tasks: %s (instance=%s sender=%s)",
            task_name,
            data.get("instance_name", ""),
            data.get("sender", ""),
        )
        return {"status": "enqueued", "task": task_name}
    except Exception:
        logger.exception("Failed to enqueue Cloud Task — falling back to sync")
        return await _process_message_webhook(data, request)


import re as _re


def _find_poll_updates(payload: dict) -> list | None:
    """Exhaustively search for pollUpdates in any nesting of the payload.

    Evolution API sends poll votes in different shapes depending on version:
      - data.pollUpdates                       (v2 messages.upsert)
      - data.update.pollUpdates                (v2 messages.update dict)
      - data[0].update.pollUpdates             (v2 messages.update array)
      - data[0].pollUpdates                    (alternative)
    """
    data = payload.get("data")

    # data is a dict
    if isinstance(data, dict):
        # Direct: data.pollUpdates
        pu = data.get("pollUpdates")
        if isinstance(pu, list) and pu:
            return pu
        # Nested: data.update.pollUpdates
        update = data.get("update")
        if isinstance(update, dict):
            pu = update.get("pollUpdates")
            if isinstance(pu, list) and pu:
                return pu
        # Nested: data.message.pollUpdateMessage exists → check sibling pollUpdates
        msg = data.get("message")
        if isinstance(msg, dict) and "pollUpdateMessage" in msg:
            # pollUpdates should be at data level
            pu = data.get("pollUpdates")
            if isinstance(pu, list) and pu:
                return pu

    # data is a list (messages.update array format)
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            pu = item.get("pollUpdates")
            if isinstance(pu, list) and pu:
                return pu
            update = item.get("update")
            if isinstance(update, dict):
                pu = update.get("pollUpdates")
                if isinstance(pu, list) and pu:
                    return pu

    return None


def _find_poll_voter(payload: dict, poll_updates: list) -> str:
    """Extract the voter JID from the payload, trying multiple locations."""
    # 1. From pollUpdates[0].pollUpdateMessageKey
    voter = _extract_poll_voter(poll_updates)
    if voter:
        return voter

    data = payload.get("data")

    # 2. From data.key.remoteJid (single dict format)
    if isinstance(data, dict):
        key = data.get("key", {})
        if isinstance(key, dict):
            jid = key.get("remoteJid", "")
            if jid and not jid.endswith("@g.us"):
                return jid

    # 3. From data[0].key.remoteJid (array format)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                key = item.get("key", {})
                if isinstance(key, dict):
                    jid = key.get("remoteJid", "")
                    if jid and not jid.endswith("@g.us"):
                        return jid

    return ""


def _extract_poll_vote_text(poll_updates: list) -> str:
    """Extract human-readable vote text from Evolution pollUpdates array.

    Evolution API v2 sends poll results in two possible formats:

    Format A (aggregated, from messages.upsert):
      [{"name": "Option A", "voters": ["jid@lid"]}, {"name": "Option B", "voters": []}]
      → We pick the option(s) that have non-empty voters.

    Format B (individual vote, from messages.update):
      [{"vote": ["Option A"], "pollUpdateMessageKey": {...}}]
      → We read the vote array directly.
    """
    if not poll_updates:
        return ""

    # Try Format A first: [{name, voters}, ...]
    selected = []
    for item in poll_updates:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        voters = item.get("voters", [])
        if name and isinstance(voters, list) and voters:
            selected.append(name)
    if selected:
        return ", ".join(selected)

    # Try Format B: [{vote: ["Option"], ...}]
    first = poll_updates[0] if poll_updates else {}
    if isinstance(first, dict):
        votes = first.get("vote", [])
        if isinstance(votes, list) and votes:
            return ", ".join(str(v) for v in votes)

    return ""


def _extract_poll_voter(poll_updates: list) -> str:
    """Extract the voter's JID from the pollUpdates array.

    Evolution API v2 puts the voter info in
    ``pollUpdates[].pollUpdateMessageKey.participant`` or, for 1:1
    chats, in ``pollUpdates[].pollUpdateMessageKey.remoteJid``.
    """
    if not poll_updates:
        return ""
    first = poll_updates[0] if isinstance(poll_updates, list) else {}
    if not isinstance(first, dict):
        return ""
    key = first.get("pollUpdateMessageKey", {})
    if not isinstance(key, dict):
        return ""
    # In groups the voter is `participant`; in 1:1 it's `remoteJid`
    voter = key.get("participant") or key.get("remoteJid", "")
    return voter


_CLAIM_PATTERN = _re.compile(
    r"\b(tomo|acepto|yo|lo\s+tomo|yo\s+voy|va)\b", _re.IGNORECASE,
)


async def _resolve_tenant_from_instance_name(
    db: AsyncSession, instance_name: str,
) -> UUID | None:
    """Resolve tenant_id for a webhook instance using the scoped RLS lookup."""
    from sqlalchemy import text as sql_text

    await set_instance_lookup_context(db, instance_name)
    result = await db.execute(
        sql_text(
            "SELECT tenant_id "
            "FROM evolution_instances "
            "WHERE instance_name = :instance_name AND activo = true "
            "LIMIT 1"
        ),
        {"instance_name": instance_name},
    )
    return result.scalar_one_or_none()


async def _handle_group_message(
    raw_data: dict, incoming: WhatsAppIncoming, request: Request,
) -> dict:
    """Route a WhatsApp group message.

    Only messages from a recognised driver group (``grupo_repartidores_jid``
    on sucursales) are processed.  If the message text matches a claim
    keyword (e.g. "TOMO"), we call the delivery-claim endpoint on
    api_execute.  All other group messages are silently dropped.
    """
    group_jid = raw_data.get("_group_jid", "")
    participant = raw_data.get("_participant_jid", "")
    text = incoming.message or ""
    instance_name = incoming.instance_name

    if not group_jid or not participant:
        return {"status": "ignored", "reason": "missing_group_data"}

    # Check if this group is a recognised driver group for any tenant
    settings = request.app.state.settings
    session_factory = request.app.state.session_factory
    async with session_factory() as db:
        from sqlalchemy import text as sql_text
        tenant_id = await _resolve_tenant_from_instance_name(db, instance_name)
        if tenant_id is None:
            logger.debug("Unknown instance %s for driver-group message", instance_name)
            return {"status": "ignored", "reason": "unknown_instance"}

        await set_tenant_context(db, str(tenant_id))
        result = await db.execute(
            sql_text(
                "SELECT s.tenant_id, s.nombre AS sucursal_nombre "
                "FROM sucursales s "
                "WHERE s.tenant_id = :tid "
                "AND s.grupo_repartidores_jid = :gjid "
                "AND s.activo = true "
                "LIMIT 1"
            ),
            {"tid": str(tenant_id), "gjid": group_jid},
        )
        row = result.mappings().first()

    if not row:
        logger.debug("Group %s is not a recognised driver group — ignoring", group_jid)
        return {"status": "ignored", "reason": "unknown_group"}

    # Check for claim keywords
    if not _CLAIM_PATTERN.search(text):
        logger.debug("Group message from %s is not a claim: %s", participant, text[:50])
        return {"status": "ignored", "reason": "no_claim_keyword"}

    # Extract phone number from participant JID (e.g. "56912345678@s.whatsapp.net")
    driver_phone = participant.split("@")[0]

    # Look up driver name from repartidores table if registered
    driver_nombre = driver_phone  # fallback
    async with session_factory() as db:
        from sqlalchemy import text as sql_text
        await set_tenant_context(db, str(tenant_id))
        rep_result = await db.execute(
            sql_text(
                "SELECT nombre FROM repartidores "
                "WHERE tenant_id = :tid AND phone = :phone AND activo = true "
                "LIMIT 1"
            ),
            {"tid": str(tenant_id), "phone": driver_phone},
        )
        rep_row = rep_result.scalar_one_or_none()
        if rep_row:
            driver_nombre = rep_row

    # Call api_execute delivery claim endpoint
    headers = whatsapp_service._service_headers(
        settings, tenant_id,
        audience="api_execute",
        scopes=("comandas:write",),
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    claim_url = f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/delivery/claim"
    try:
        # Find the latest pending delivery to claim
        async with session_factory() as db:
            from sqlalchemy import text as sql_text
            await set_tenant_context(db, str(tenant_id))
            pending = await db.execute(
                sql_text(
                    "SELECT comanda_id FROM delivery_assignments "
                    "WHERE tenant_id = :tid AND estado = 'PUBLICADO' "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"tid": str(tenant_id)},
            )
            comanda_id = pending.scalar_one_or_none()

        if not comanda_id:
            # No pending deliveries — inform the driver
            await whatsapp_service.send_message(
                to=group_jid,
                message="No hay pedidos delivery pendientes en este momento.",
                instance_name=instance_name,
                settings=settings,
            )
            return {"status": "no_pending_deliveries"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                claim_url,
                json={
                    "comanda_id": str(comanda_id),
                    "repartidor_phone": driver_phone,
                    "repartidor_nombre": driver_nombre,
                },
                headers=headers,
            )

        if resp.status_code == 200:
            logger.info(
                "Delivery claimed: comanda=%s by driver=%s (%s)",
                comanda_id, driver_phone, driver_nombre,
            )
            await whatsapp_service.send_message(
                to=group_jid,
                message=f"Pedido asignado a *{driver_nombre}* ({driver_phone}). Gracias!",
                instance_name=instance_name,
                settings=settings,
            )
            return {"status": "claimed", "comanda_id": str(comanda_id)}

        if resp.status_code == 409:
            logger.info("Delivery already claimed: comanda=%s, driver=%s tried", comanda_id, driver_phone)
            await whatsapp_service.send_message(
                to=group_jid,
                message="Este pedido ya fue tomado por otro repartidor.",
                instance_name=instance_name,
                settings=settings,
            )
            return {"status": "already_claimed"}

        logger.warning("Delivery claim failed: status=%d body=%s", resp.status_code, resp.text[:200])
        return {"status": "claim_error", "detail": resp.text[:200]}

    except Exception:
        logger.exception("Error processing driver claim from group %s", group_jid)
        return {"status": "error"}


async def _process_message_webhook(data: dict, request: Request) -> dict:
    session_factory = request.app.state.session_factory
    async with session_factory() as db:
        try:
            await set_instance_lookup_context(db, data["instance_name"])
            result = await whatsapp_service.process_incoming(
                data,
                request.app.state.settings,
                db,
                _session_factory=session_factory,
            )
            await db.commit()
        except (SQLAlchemyError, httpx.HTTPError, RuntimeError, ValueError) as exc:
            await db.rollback()
            logger.exception("Error processing incoming WhatsApp message")
            raise _webhook_error() from exc
    return {"status": "processed", "detail": result}


def _is_connection_update(payload: dict[str, Any]) -> bool:
    event = payload.get("event", "")
    if event in {"connection.update", "CONNECTION_UPDATE"}:
        return True
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return False
    if "state" not in data:
        return False
    if data.get("key") or data.get("message"):
        return False
    return True


async def _handle_connection_update(payload: dict[str, Any], request: Request) -> dict:
    instance_name = payload.get("instance", "")
    if not instance_name:
        return {"status": "ignored", "reason": "no_instance_name"}

    db_status = _connection_state(payload)
    session_factory = request.app.state.session_factory
    async with session_factory() as db:
        try:
            await set_instance_lookup_context(db, instance_name)
            result = await instance_service.update_status(db, instance_name, db_status)
            await db.commit()
        except (SQLAlchemyError, ValueError):
            await db.rollback()
            logger.exception("Error handling CONNECTION_UPDATE for %s", instance_name)
            return {"status": "error"}
    if result is None:
        return {"status": "ignored", "reason": "unknown_instance"}
    logger.info("CONNECTION_UPDATE: %s -> %s", instance_name, db_status)
    return {"status": "connection_updated", "state": db_status}


def _connection_state(payload: dict[str, Any]) -> str:
    state = payload.get("data", {}).get("state", "unknown")
    return "CONNECTED" if state == "open" else "DISCONNECTED"


def _extract_sender(payload: dict[str, Any]) -> tuple[dict, dict, str] | None:
    """Extract and validate data, key, and sender from Evolution payload.

    Group messages (@g.us) are allowed but marked with metadata so the
    downstream handler can route them to the driver-claim flow instead of
    the normal AI pipeline.  Other unsupported JID types are discarded.
    """
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return None
    key = data.get("key", {})
    if not isinstance(key, dict):
        return None
    sender = key.get("remoteJid", "")
    if not sender:
        return None

    # Block broadcast / newsletter only. For LID-addressed messages
    # (WhatsApp's newer Logical ID format), prefer `remoteJidAlt` when
    # present — it carries the classic phone@s.whatsapp.net form that
    # our downstream flow expects. Otherwise rebuild it from the digits.
    if sender.endswith(("@broadcast", "@newsletter")):
        logger.info("Ignoring unsupported JID type: %s", sender)
        return None
    if sender.endswith("@lid"):
        # LID digits are an opaque identifier, NOT the phone number, so we
        # never rebuild a JID from them (that creates leads under a wrong
        # phone and replies go nowhere). Use the alt fields Baileys provides
        # alongside LID-addressed messages; without one, drop the message.
        alt = next(
            (
                value.split(":")[0].split("@")[0] + "@s.whatsapp.net"
                for field in ("remoteJidAlt", "senderPn", "previousRemoteJid")
                if (value := key.get(field, ""))
                and isinstance(value, str)
                and not value.endswith("@lid")
                and value.split(":")[0].split("@")[0].isdigit()
            ),
            "",
        )
        if alt:
            logger.info("Mapping LID sender %s -> %s", sender, alt)
            sender = alt
            key["remoteJid"] = alt
        else:
            logger.warning(
                "Dropping LID sender without phone alt (remoteJidAlt/senderPn): %s",
                sender,
            )
            return None

    # Allow group messages but tag them for special routing
    if sender.endswith("@g.us"):
        participant = key.get("participant", "")
        if not participant:
            logger.info("Ignoring group message without participant: %s", sender)
            return None
        data["_is_group"] = True
        data["_group_jid"] = sender
        data["_participant_jid"] = participant  # actual sender phone@s.whatsapp.net

    return data, key, sender


def _extract_text_and_media(data: dict) -> tuple[str, dict | None]:
    """Extract message text and media info from Evolution data.

    Handles regular text, media captions, interactive list selections,
    and poll vote responses (where readable votes live in data.pollUpdates).
    """
    # Poll vote responses: votes are in data.pollUpdates, not data.message
    poll_updates = data.get("pollUpdates")
    if isinstance(poll_updates, list) and poll_updates:
        first_update = poll_updates[0]
        votes = first_update.get("vote", []) if isinstance(first_update, dict) else []
        if votes:
            vote_text = ", ".join(str(v) for v in votes)
            logger.info("Poll vote extracted: %s", vote_text)
            return vote_text, None

    message_obj = data.get("message")
    text = whatsapp_service.extract_message_text(message_obj)
    media_info = detect_media_from_payload(message_obj) if isinstance(message_obj, dict) else None
    if media_info:
        logger.info("Media detected in webhook: type=%s mimetype=%s", media_info.get("media_type"), media_info.get("mimetype"))
    return text, media_info


def _build_incoming(
    sender: str, text: str, media_info: dict | None,
    key: dict, payload: dict,
) -> WhatsAppIncoming:
    """Build a WhatsAppIncoming from parsed components."""
    incoming = WhatsAppIncoming(
        sender=sender,
        message=text or (media_info.get("caption", "") if media_info else ""),
        instance_name=payload.get("instance", ""),
        from_me=bool(key.get("fromMe", False)),
    )
    if media_info:
        incoming.media_type = media_info["media_type"]
        incoming.mimetype = media_info.get("mimetype")
        incoming.file_name = media_info.get("file_name")
    return incoming


def _parse_evolution_payload(payload: dict[str, Any]) -> WhatsAppIncoming | None:
    extracted = _extract_sender(payload)
    if extracted is None:
        logger.debug("Webhook ignored: no valid sender extracted (event=%s)", payload.get("event", ""))
        return None
    data, key, sender = extracted

    text, media_info = _extract_text_and_media(data)
    if not text and not media_info:
        logger.warning(
            "Ignoring WhatsApp webhook without extractable message or media: instance=%s sender=%s",
            payload.get("instance", ""), sender,
        )
        return None

    return _build_incoming(sender, text, media_info, key, payload)


def _webhook_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to process incoming WhatsApp message",
    )


def _settings_error(instance_name: str) -> HTTPException:
    logger.exception("Failed to configure instance %s", instance_name)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to configure WhatsApp instance settings",
    )


def _history_sync_error(instance_name: str) -> HTTPException:
    logger.exception("Failed to sync historical messages for %s", instance_name)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to sync WhatsApp history",
    )
