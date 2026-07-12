"""WhatsApp messaging via Evolution API."""

import asyncio
import base64
import json
import logging
import random
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import CanalesSettings
from app.services import instance_service
from app.services.text_format import markdown_to_whatsapp
from shared.database import set_tenant_context
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import HttpClient, internal_http

logger = logging.getLogger(__name__)

# Respuesta casi-instantánea ("balanceado"): suficiente para parecer humano y no
# disparar el anti-spam de WhatsApp, pero sin la espera artificial de varios segundos.
# La presencia "composing" cubre la óptica anti-baneo.
_REPLY_DELAY_MIN = 0.3
_REPLY_DELAY_MAX = 0.6
_EXTRAS_DELAY_MIN = 0.3
_EXTRAS_DELAY_MAX = 0.6
# Re-asserts "composing" every N seconds during a slow LLM round-trip so the
# WhatsApp typing bubble does not expire before the reply lands.
_COMPOSING_REFRESH_SECONDS = 5.0
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_MESSAGES = 30
_DEFAULT_DEBOUNCE_SECONDS = 0.9
_MAX_DEBOUNCE_SECONDS = 15.0
MESSAGE_WRAPPER_KEYS = (
    "ephemeralMessage",
    "viewOnceMessage",
    "viewOnceMessageV2",
    "viewOnceMessageV2Extension",
)
_instance_send_history: dict[str, deque[float]] = {}

# ── Debounce buffer: groups consecutive messages per (tenant, phone) ──
# Each entry: {"messages": [...], "timer": asyncio.TimerHandle, "data": {...}}
_debounce_buffers: dict[tuple[str, str], dict[str, Any]] = {}
_debounce_lock = asyncio.Lock()


def _normalize_phone(remote_jid: str) -> str:
    return remote_jid.split("@")[0] if "@" in remote_jid else remote_jid


def extract_message_text(message: Any) -> str:
    """Normalize Evolution payload variants and extract user-visible text."""
    normalized = _normalize_message(message)
    text = _extract_text(normalized)
    if not text and normalized:
        logger.warning("Unsupported WhatsApp payload structure: %s", normalized)
    return text


def _service_headers(
    settings: CanalesSettings,
    tenant_id: UUID,
    *,
    audience: str,
    scopes: tuple[str, ...],
) -> dict[str, str]:
    return build_service_auth_headers(
        service_name="canales_service",
        audience=audience,
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=scopes,
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )


async def send_message(
    to: str,
    message: str,
    instance_name: str,
    settings: CanalesSettings,
) -> dict:
    _enforce_send_rate_limit(instance_name)
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    headers = {"apikey": settings.EVOLUTION_API_KEY}
    payload = {"number": to, "text": message}
    response = await client.post(f"/message/sendText/{instance_name}", headers=headers, json=payload)
    response.raise_for_status()
    logger.info("WhatsApp message sent to %s via %s", to, instance_name)
    return response.json()


async def _resolve_lead_phone(
    lead_id: UUID, tenant_id: UUID, settings: CanalesSettings,
) -> str:
    """Look up lead phone or raise RuntimeError."""
    headers = _service_headers(settings, tenant_id, audience="api_execute", scopes=("leads:read",))
    phone = await _get_lead_phone(lead_id, tenant_id, settings, headers)
    if not phone:
        raise RuntimeError(f"Could not resolve phone for lead {lead_id}")
    return phone


async def _persist_reply_history(
    tenant_id: UUID, lead_id: UUID, message: str | None,
    caption: str | None, media_url: str | None, media_type: str | None,
    settings: CanalesSettings,
) -> None:
    """Build and store conversation history entry for a human reply."""
    content = message or caption or f"[{(media_type or 'media').upper()}]"
    headers = _service_headers(settings, tenant_id, audience="api_execute", scopes=("conversations:import",))
    await _import_historical_messages(
        tenant_id=tenant_id, lead_id=lead_id,
        messages=[_build_history_msg("assistant", content, media_url, media_type)],
        settings=settings, auth_headers=headers,
    )


async def send_human_reply(
    lead_id: UUID, message: str | None, tenant_id: UUID,
    instance_name: str, settings: CanalesSettings,
    *, media_url: str | None = None, media_type: str | None = None,
    file_name: str | None = None, caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Send a human agent reply (text and/or media) and persist it in conversation history."""
    phone = await _resolve_lead_phone(lead_id, tenant_id, settings)
    message_id = await _send_outbound_content(
        phone, message, instance_name, settings,
        media_url=media_url, media_type=media_type,
        file_name=file_name, caption=caption or message, mimetype=mimetype,
    )
    await _persist_reply_history(
        tenant_id, lead_id, message, caption, media_url, media_type, settings,
    )
    logger.info("Human reply sent to lead %s via %s (has_media=%s)", lead_id, instance_name, bool(media_url))
    return {"message_id": message_id}


async def _get_lead_phone(
    lead_id: UUID,
    tenant_id: UUID,
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> str | None:
    try:
        response = await internal_http.get(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads/{lead_id}",
            headers=_tenant_headers(tenant_id, auth_headers),
        )
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to fetch lead %s for phone lookup", lead_id)
        return None
    if response.status_code != 200:
        return None
    body = response.json()
    data = body.get("data", body) if isinstance(body, dict) else body
    return data.get("telefono") if isinstance(data, dict) else None


async def _resolve_outbound_message(
    message: str | None,
    use_ai: bool,
    lead_id: UUID,
    tenant_id: UUID,
    settings: CanalesSettings,
) -> str | None:
    """Determine the final message text, optionally via AI."""
    if use_ai and message:
        ai_result = await _forward_to_ai(message, lead_id, tenant_id, settings)
        if ai_result is None:
            raise RuntimeError("AI reply generation unreachable for outbound message")
        return ai_result.get("response", message)
    return message


async def _send_outbound_content(
    phone: str,
    final_message: str | None,
    instance_name: str,
    settings: CanalesSettings,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> str | None:
    """Send text or media via Evolution API. Returns message_id or None."""
    from app.services.media_service import send_media_via_evolution

    formatted_message = markdown_to_whatsapp(final_message) if final_message else None
    if media_url and media_type:
        media_result = await send_media_via_evolution(
            to=phone, media_url=media_url, media_type=media_type,
            instance_name=instance_name, settings=settings,
            file_name=file_name, caption=caption or formatted_message, mimetype=mimetype,
        )
        return media_result.get("key", {}).get("id")
    if formatted_message:
        result = await send_message(phone, formatted_message, instance_name, settings)
        return result.get("key", {}).get("id")
    return None


async def send_outbound(
    lead_id: UUID,
    message: str | None,
    use_ai: bool,
    tenant_id: UUID,
    instance_name: str,
    settings: CanalesSettings,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Send an outbound WhatsApp message (text and/or media) to a lead."""
    api_execute_headers = _service_headers(
        settings, tenant_id, audience="api_execute", scopes=("leads:read",),
    )
    ai_import_headers = _service_headers(
        settings, tenant_id, audience="api_execute", scopes=("conversations:import",),
    )

    phone = await _get_lead_phone(lead_id, tenant_id, settings, api_execute_headers)
    if not phone:
        raise RuntimeError(f"Could not resolve phone for lead {lead_id}")

    final_message = await _resolve_outbound_message(
        message, use_ai, lead_id, tenant_id, settings,
    )
    message_id = await _send_outbound_content(
        phone, final_message, instance_name, settings,
        media_url=media_url, media_type=media_type,
        file_name=file_name, caption=caption, mimetype=mimetype,
    )

    content = final_message or caption or f"[{(media_type or 'media').upper()}]"
    await _import_historical_messages(
        tenant_id=tenant_id, lead_id=lead_id,
        messages=[_build_history_msg("assistant", content, media_url, media_type)],
        settings=settings, auth_headers=ai_import_headers,
    )

    logger.info("Outbound message sent to lead %s via %s (use_ai=%s, has_media=%s)", lead_id, instance_name, use_ai, bool(media_url))
    return {"message_id": message_id}


async def _fetch_ai_config(
    tenant_id: UUID,
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> dict:
    """Fetch the tenant's agente_config once from api_execute.

    Returns the parsed body, or {} if unavailable so callers fall back to
    defaults. A single GET feeds both the auto-response flag and the debounce
    window (they used to be two separate round-trips to the same endpoint).
    """
    try:
        response = await internal_http.get(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/ai/config",
            headers=_tenant_headers(tenant_id, auth_headers),
        )
        if response.status_code == 200:
            return response.json()
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to fetch agente_config for tenant %s, using defaults", tenant_id)
    return {}


def _auto_respuesta_enabled(config: dict) -> bool:
    """Whether auto-response is on for the tenant (defaults to ON)."""
    return config.get("auto_respuesta_whatsapp", True)


def _debounce_seconds(config: dict) -> float:
    """Debounce window from config, clamped to the max (default if absent)."""
    val = config.get("debounce_seconds")
    if val is not None:
        try:
            return min(float(val), _MAX_DEBOUNCE_SECONDS)
        except (TypeError, ValueError):
            pass
    return _DEFAULT_DEBOUNCE_SECONDS


def _build_all_headers(
    settings: CanalesSettings, tenant_id: UUID,
) -> dict[str, dict[str, str]]:
    """Build all inter-service auth header sets for incoming message processing."""
    def _h(audience: str, scopes: tuple[str, ...]) -> dict[str, str]:
        return _service_headers(settings, tenant_id, audience=audience, scopes=scopes)

    return {
        "api_read": _h("api_execute", ("leads:read",)),
        "api_write": _h("api_execute", ("leads:write",)),
        "ai_config": _h("api_execute", ("config:read",)),
        "ai_import": _h("api_execute", ("conversations:import",)),
    }


def _resolve_incoming_media(
    data: dict, media_url: str | None, media_type: str | None,
) -> tuple[str, str | None, str | None]:
    """Extract message text and media metadata from incoming data."""
    message_text = data.get("message", "")
    if media_type and not message_text:
        message_text = f"[{media_type.upper()}]"
    return message_text, media_url, media_type


def _build_history_msg(
    role: str, content: str,
    media_url: str | None = None, media_type: str | None = None,
) -> dict[str, Any]:
    """Build a history message dict with optional media metadata."""
    msg: dict[str, Any] = {
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if media_url:
        msg["media_url"] = media_url
        msg["media_type"] = media_type
    return msg


async def _store_message_only(
    tenant_id: UUID, lead_id: UUID, role: str, text: str,
    media_url: str | None, media_type: str | None,
    settings: CanalesSettings, auth_headers: dict[str, str],
) -> dict:
    """Store a message without triggering AI response."""
    await _import_historical_messages(
        tenant_id=tenant_id, lead_id=lead_id,
        messages=[_build_history_msg(role, text, media_url, media_type)],
        settings=settings, auth_headers=auth_headers,
    )
    status = "stored_outbound" if role == "assistant" else "stored"
    return {"status": status, "lead_id": str(lead_id)}


def _list_to_numbered_text(list_data: dict) -> str:
    """Render a WhatsApp list payload as a numbered text menu (1), 2), 3)…).

    WhatsApp interactive lists are no longer sent; the same options are shown as
    plain text so the customer can reply with the option number. Numbering is
    continuous across sections; section titles are kept as italic headers.
    """
    title = (list_data.get("title") or "").strip()
    blocks: list[str] = []
    n = 0
    for section in list_data.get("sections", []):
        sec_lines: list[str] = []
        sec_title = (section.get("title") or "").strip()
        if sec_title:
            sec_lines.append(f"_{sec_title}_")
        for row in section.get("rows", []):
            row_title = (row.get("title") or "").strip()
            if not row_title:
                continue
            n += 1
            desc = (row.get("description") or "").strip()
            sec_lines.append(f"{n}) {row_title}" + (f" — {desc}" if desc else ""))
        if sec_lines:
            blocks.append("\n".join(sec_lines))
    body = "\n\n".join(blocks)
    if title and body:
        return f"*{title}*\n\n{body}"
    return f"*{title}*" if title else body

#El proposito de esta funcion es enviar las extras de la respuesta de la IA, como poll, list, y media.
async def _send_interactive_extras(
    ai_result: dict, phone: str, instance_name: str, settings: CanalesSettings,
) -> None:
    """Send poll, list, and media extras returned by the AI orchestrator.

    Adds a short delay before each extra to avoid overwhelming the customer
    with multiple messages arriving simultaneously.
    """
    # Mirror the real per-extra send guards below: primary media is only sent
    # when BOTH media_url and media_type are present (see media block), so do not
    # fire the "composing" presence for a media_url that has no media_type.
    has_extras = bool(
        ai_result.get("poll")
        or ai_result.get("list_message")
        or ai_result.get("preview_image_url")
        or (ai_result.get("media_url") and ai_result.get("media_type"))
    )
    if has_extras:
        asyncio.ensure_future(send_presence(phone, instance_name, settings, "composing"))
        await asyncio.sleep(random.uniform(_EXTRAS_DELAY_MIN, _EXTRAS_DELAY_MAX))

    poll_data = ai_result.get("poll")
    if poll_data:
        try:
            await send_poll(
                phone, poll_data["question"], poll_data["options"],
                instance_name, settings,
                selectable_count=poll_data.get("selectable_count", 1),
            )
        except (httpx.HTTPError, RuntimeError):
            logger.warning("Failed to send poll to %s", phone, exc_info=True)

    # WhatsApp interactive lists are disabled — present the options as a
    # numbered text menu (1), 2), 3)…) so the customer can reply with the number.
    list_data = ai_result.get("list_message")
    if list_data:
        options_text = _list_to_numbered_text(list_data)
        if options_text:
            try:
                await send_message(phone, options_text, instance_name, settings)
            except (httpx.HTTPError, RuntimeError):
                logger.warning("Failed to send numbered options to %s", phone, exc_info=True)

    # Preview image (menu header / branding) — sent BEFORE the document
    preview_url = ai_result.get("preview_image_url")
    if preview_url:
        try:
            await _send_media_attachment(
                preview_url, "image", phone, instance_name, settings,
                file_name="menu-cabecera.jpg",
                caption=ai_result.get("preview_image_caption"),
            )
        except (httpx.HTTPError, RuntimeError):
            logger.warning("Failed to send preview image to %s", phone, exc_info=True)

    # Primary media attachment (PDF, image, etc.)
    ai_media_url = ai_result.get("media_url")
    ai_media_type = ai_result.get("media_type")
    if ai_media_url and ai_media_type:
        await _send_media_attachment(
            ai_media_url, ai_media_type, phone, instance_name, settings,
            file_name=ai_result.get("media_file_name"),
            caption=ai_result.get("media_caption"),
        )


async def _forward_and_reply(
    message_text: str, lead_id: UUID, tenant_id: UUID,
    phone: str, instance_name: str, contact_id: str | None,
    media_url: str | None, media_type: str | None,
    settings: CanalesSettings, headers: dict[str, dict[str, str]],
    t0: float,
) -> dict:
    """Forward message to AI, send reply, handle media and FSM."""
    # Keep the "typing…" bubble alive across the LLM round-trip and clear it
    # explicitly once we are done, so it neither drops before a slow reply nor
    # lingers/reappears after a fast one.
    typing = asyncio.ensure_future(_keep_composing(phone, instance_name, settings))
    try:
        ai_result = await _forward_to_ai(
            message_text, lead_id, tenant_id, settings,
            contact_id=contact_id, media_url=media_url, media_type=media_type,
        )
        if ai_result is None:
            return {"status": "error", "reason": "ai_orchestrator_unreachable"}

        reply_text = (ai_result.get("response") or "").strip()

        # If AI returned TTS audio, send as WhatsApp voice message
        audio_b64 = ai_result.get("audio_base64")
        logger.info("TTS audio check: has_audio=%s keys=%s", bool(audio_b64), [k for k in ai_result if 'audio' in k.lower()] if ai_result else [])
        if audio_b64 and reply_text:
            reply_result = await _send_tts_audio_reply(
                audio_b64, reply_text, phone, instance_name, tenant_id, settings,
            )
        else:
            reply_result = await _send_reply(
                reply_text, phone, instance_name, settings, lead_id,
            )

        # Per-message latency metric (parsed by a dashboard). Emit exactly one line
        # when an actual AI auto-reply was successfully sent to the customer:
        # inbound text, reply text, and arrival→reply-sent latency. Never raises.
        if reply_text and reply_result.get("status") == "replied":
            try:
                logger.info("WA_LATENCY %s", json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "tenant": str(tenant_id),
                    "phone": phone,
                    "latency_s": round(time.time() - t0, 2),
                    "inbound": (message_text or "")[:200],
                    "reply": (reply_text or "")[:200],
                }, ensure_ascii=False))
            except Exception:
                logger.debug("Failed to emit WA_LATENCY metric", exc_info=True)

        await _send_interactive_extras(ai_result, phone, instance_name, settings)

        if reply_result.get("status") == "replied" and lead_id is not None:
            asyncio.ensure_future(
                _progress_lead_estado(lead_id, tenant_id, settings, headers["api_write"])
            )
        return reply_result
    finally:
        typing.cancel()
        asyncio.ensure_future(
            send_presence(phone, instance_name, settings, "paused", delay_ms=0)
        )


async def _resolve_incoming_lead(
    phone: str, tenant_id: UUID, settings: CanalesSettings, headers: dict,
) -> UUID | None:
    """Find or create a lead for an incoming message."""
    return await _find_or_create_lead(
        phone, tenant_id, settings,
        api_read_headers=headers["api_read"],
        api_write_headers=headers["api_write"],
    )


def _extract_media(data: dict) -> tuple[str | None, str | None]:
    """Extract media_url and media_type from webhook data."""
    return data.get("media_url"), data.get("media_type")


async def _resolve_media_and_text(
    data: dict, instance, settings, tenant_id, headers: dict,
) -> tuple[str, str | None, str | None]:
    """Resolve message text, media URL, and media type from incoming data."""
    media_url, raw_media_type = _extract_media(data)
    transcription = None
    if raw_media_type == "audio" and not media_url:
        try:
            media_url, transcription = await _handle_incoming_audio(
                data, instance, settings, tenant_id, headers,
            )
        except Exception:
            logger.warning("Audio handling failed, continuing without media", exc_info=True)
            media_url, transcription = None, None
    elif raw_media_type and raw_media_type != "audio" and not media_url:
        try:
            media_url = await _handle_incoming_media(data, instance, settings, tenant_id)
        except Exception:
            logger.warning("Media upload failed, continuing without media", exc_info=True)
            media_url = None

    message_text, media_url, media_type = _resolve_incoming_media(data, media_url, raw_media_type)
    if transcription:
        message_text = transcription
        data["message"] = transcription
    elif raw_media_type == "audio" and not message_text:
        message_text = "[El cliente envió una nota de voz que no se pudo transcribir]"
        data["message"] = message_text
    return message_text, media_url, media_type


async def _try_debounce(
    data: dict, message_text: str, tenant_id, phone: str,
    lead_id, media_url, media_type, settings, headers: dict,
    skip_debounce: bool, session_factory, debounce_secs: float,
) -> dict | None:
    """Try to debounce the message. Returns response dict if debounced, else None."""
    if skip_debounce or session_factory is None or debounce_secs <= 0:
        return None
    buffered = await _enqueue_debounce(
        data, message_text, tenant_id, phone,
        debounce_secs, settings, session_factory,
    )
    if not buffered:
        return None
    await _store_message_only(
        tenant_id, lead_id, "user", message_text,
        media_url, media_type, settings, headers["ai_import"],
    )
    return {"status": "debounced", "lead_id": str(lead_id)}


async def _route_incoming_message(
    data: dict, message_text: str, media_url: str | None, media_type: str | None,
    tenant_id: UUID, lead_id: UUID, phone: str, contact_id: str | None,
    instance_name: str, settings: CanalesSettings, headers: dict,
    skip_debounce: bool, session_factory: Any, t0: float,
) -> dict:
    """Route an incoming message: store, debounce, or forward to AI."""
    if data.get("from_me", False):
        return await _store_message_only(
            tenant_id, lead_id, "assistant", message_text,
            media_url, media_type, settings, headers["ai_import"],
        )

    # One GET to /api/v1/ai/config feeds both the auto-response flag and the
    # debounce window (previously two separate round-trips to the same endpoint).
    config = await _fetch_ai_config(tenant_id, settings, headers["ai_config"])
    if not _auto_respuesta_enabled(config):
        logger.info("Auto-response disabled for tenant %s", tenant_id)
        return await _store_message_only(
            tenant_id, lead_id, "user", message_text,
            media_url, media_type, settings, headers["ai_import"],
        )

    debounced = await _try_debounce(
        data, message_text, tenant_id, phone, lead_id,
        media_url, media_type, settings, headers, skip_debounce, session_factory,
        _debounce_seconds(config),
    )
    if debounced is not None:
        return debounced

    return await _forward_and_reply(
        message_text, lead_id, tenant_id, phone, instance_name,
        contact_id, media_url, media_type, settings, headers, t0,
    )


async def process_incoming(
    data: dict, settings: CanalesSettings, db: AsyncSession,
    *, _skip_debounce: bool = False, _session_factory: Any = None,
) -> dict:
    """Process an incoming WhatsApp message webhook."""
    instance = await instance_service.lookup_by_instance_name(db, data["instance_name"])
    if instance is None:
        logger.warning("Unknown instance in webhook: %s", data["instance_name"])
        return {"status": "ignored", "reason": "unknown_instance"}

    phone = _normalize_phone(data["sender"])
    tenant_id = instance.tenant_id
    # Inbound-arrival timestamp for the per-message latency metric (WA_LATENCY):
    # captured at the very start of inbound processing so the dashboard can show
    # how long it took from arrival to the auto-reply being sent.
    t0 = time.time()
    # Fire "typing…" presence immediately (within ~100ms), before the pre-LLM
    # hops + debounce wait, so the customer sees activity right away. Skip
    # echoes of our own outbound messages (from_me).
    if not data.get("from_me", False):
        asyncio.ensure_future(
            send_presence(phone, instance.instance_name, settings, "composing")
        )
    await set_tenant_context(db, str(tenant_id))
    _ts_tenant = time.time()

    headers = _build_all_headers(settings, tenant_id)
    _ts_headers = time.time()
    lead_id = await _resolve_incoming_lead(phone, tenant_id, settings, headers)
    _ts_lead = time.time()
    if lead_id is None:
        logger.warning("Could not resolve lead for phone %s (tenant %s)", phone, tenant_id)
        return {"status": "skipped", "reason": "lead_resolution_failed"}

    # Contacts are not a separate entity in this deployment (the customer chat
    # keys off the lead), so no contact resolution round-trip is made.
    contact_id = None
    message_text, media_url, media_type = await _resolve_media_and_text(
        data, instance, settings, tenant_id, headers,
    )
    _ts_gather = time.time()
    # WA_STAGE: per-stage timing of the pre-LLM canales path, to pin which call
    # eats the ~5s stalls seen in WA_LATENCY (set_tenant_context vs headers/jwt
    # vs /leads HTTP vs media resolution). Purely additive, no new branches.
    logger.info("WA_STAGE %s", json.dumps({
        "tenant": str(tenant_id),
        "phone": phone,
        "tenant_ms": round((_ts_tenant - t0) * 1000),
        "headers_ms": round((_ts_headers - _ts_tenant) * 1000),
        "lead_ms": round((_ts_lead - _ts_headers) * 1000),
        "gather_ms": round((_ts_gather - _ts_lead) * 1000),
        "pre_ms": round((_ts_gather - t0) * 1000),
    }, ensure_ascii=False))

    return await _route_incoming_message(
        data, message_text, media_url, media_type,
        tenant_id, lead_id, phone, contact_id, instance.instance_name,
        settings, headers, _skip_debounce, _session_factory, t0,
    )


async def _send_tts_audio_reply(
    audio_b64: str,
    reply_text: str,
    phone: str,
    instance_name: str,
    tenant_id: UUID,
    settings: CanalesSettings,
) -> dict:
    """Upload TTS audio to GCS and send as WhatsApp voice message."""
    from app.services.media_service import send_media_via_evolution, upload_media_to_gcs

    try:
        audio_bytes = base64.b64decode(audio_b64)
        _, signed_url = await upload_media_to_gcs(
            audio_bytes, tenant_id, "audio", "audio/mpeg", settings,
        )
        await asyncio.sleep(random.uniform(_REPLY_DELAY_MIN, _REPLY_DELAY_MAX))
        await send_media_via_evolution(
            to=phone,
            media_url=signed_url,
            media_type="audio",
            instance_name=instance_name,
            settings=settings,
            file_name="respuesta.mp3",
            mimetype="audio/mpeg",
        )
        logger.info("TTS audio reply sent to %s", phone)
        return {"status": "replied", "type": "audio"}
    except Exception:
        logger.exception("TTS audio send failed for %s, falling back to text", phone)
        return await _send_reply(reply_text, phone, instance_name, settings, None)


async def _send_media_attachment(
    media_url: str,
    media_type: str,
    phone: str,
    instance_name: str,
    settings: CanalesSettings,
    file_name: str | None = None,
    caption: str | None = None,
) -> None:
    """Send a media attachment alongside the AI text reply."""
    from app.services.media_service import send_media_via_evolution

    try:
        await send_media_via_evolution(
            to=phone,
            media_url=media_url,
            media_type=media_type,
            instance_name=instance_name,
            settings=settings,
            file_name=file_name,
            caption=caption,
        )
        logger.info("AI media attachment sent to %s (type=%s)", phone, media_type)
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Failed to send AI media attachment to %s", phone)


async def _handle_incoming_audio(
    data: dict,
    instance,
    settings: CanalesSettings,
    tenant_id: UUID,
    headers: dict[str, dict[str, str]],
) -> tuple[str | None, str | None]:
    """Download incoming audio, upload to GCS, and transcribe via STT.

    Returns (signed_url, transcription). Either may be None on failure.
    """
    from app.services.media_service import download_media_from_evolution, upload_media_to_gcs

    message_id = data.get("external_wa_id") or data.get("message_id")
    sender = data.get("sender", "")
    mimetype = data.get("mimetype", "audio/ogg")

    if not message_id:
        logger.warning("Cannot download audio: no message_id in webhook data")
        return None, None

    downloaded = await download_media_from_evolution(
        instance_name=instance.instance_name,
        message_id=message_id,
        remote_jid=sender,
        settings=settings,
    )
    if not downloaded:
        return None, None

    raw_bytes, actual_mimetype = downloaded

    # Upload to GCS
    _, signed_url = await upload_media_to_gcs(
        data=raw_bytes,
        tenant_id=tenant_id,
        media_type="audio",
        mimetype=actual_mimetype or mimetype,
        settings=settings,
    )

    # No speech-to-text service in this deployment: the audio is stored and the
    # caller falls back to a placeholder transcription.
    transcription = await _transcribe_audio(
        raw_bytes, actual_mimetype or mimetype, tenant_id, settings, headers,
    )

    return signed_url, transcription


async def _transcribe_audio(
    audio_bytes: bytes,
    mimetype: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    headers: dict[str, dict[str, str]],
) -> str | None:
    """Speech-to-text is not available in this deployment.

    No STT service exists yet, so voice notes are stored as media and the caller
    uses a placeholder transcription (see ``_resolve_media_and_text``).
    TODO: reimplement transcription when an STT service is added.
    """
    return None


async def _handle_incoming_media(
    data: dict,
    instance,
    settings: CanalesSettings,
    tenant_id: UUID,
) -> str | None:
    """Download incoming media from Evolution API and upload to GCS.

    Returns the signed GCS URL or None if download/upload fails.
    """
    from app.services.media_service import download_media_from_evolution, upload_media_to_gcs

    message_id = data.get("external_wa_id") or data.get("message_id")
    sender = data.get("sender", "")
    media_type = data.get("media_type", "audio")
    mimetype = data.get("mimetype", "audio/ogg")

    if not message_id:
        logger.warning("Cannot download media: no message_id in webhook data")
        return None

    downloaded = await download_media_from_evolution(
        instance_name=instance.instance_name,
        message_id=message_id,
        remote_jid=sender,
        settings=settings,
    )
    if not downloaded:
        return None

    raw_bytes, actual_mimetype = downloaded
    _, signed_url = await upload_media_to_gcs(
        data=raw_bytes,
        tenant_id=tenant_id,
        media_type=media_type,
        mimetype=actual_mimetype or mimetype,
        settings=settings,
    )
    return signed_url


def _build_sync_headers(
    settings: CanalesSettings, tenant_id: UUID,
) -> dict[str, dict[str, str]]:
    """Build auth headers needed for history sync operations."""
    return {
        "api_read": _service_headers(settings, tenant_id, audience="api_execute", scopes=("leads:read",)),
        "api_write": _service_headers(settings, tenant_id, audience="api_execute", scopes=("leads:write",)),
        "ai_import": _service_headers(settings, tenant_id, audience="api_execute", scopes=("conversations:import",)),
    }


def _filter_supported_chats(chats: list, max_chats: int | None) -> list[dict]:
    """Filter to supported chat types and apply optional limit."""
    supported = [
        c for c in chats
        if isinstance(c, dict) and _is_supported_chat(c.get("remoteJid", ""))
    ]
    return supported[:max_chats] if max_chats is not None else supported


async def _sync_one_chat(
    chat: dict, instance_name: str, tenant_id: UUID,
    settings: CanalesSettings, headers: dict, page_size: int,
    since: datetime | None,
) -> dict:
    """Sync a single chat and return result dict."""
    remote_jid = str(chat.get("remoteJid", ""))
    try:
        chat_result = await _sync_single_chat_history(
            remote_jid=remote_jid, instance_name=instance_name,
            tenant_id=tenant_id, settings=settings,
            api_read_headers=headers["api_read"],
            api_write_headers=headers["api_write"],
            ai_import_headers=headers["ai_import"],
            page_size=page_size, since=since,
        )
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.exception("Failed to sync historical WhatsApp chat %s", remote_jid)
        return {"status": "failed", "imported": 0, "skipped": 0}
    return {
        "status": "imported" if chat_result["messages_imported"] > 0 else "empty",
        "imported": chat_result["messages_imported"],
        "skipped": chat_result["messages_skipped"],
    }


async def sync_historical_conversations(
    instance_name: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    page_size: int = 200,
    max_chats: int | None = None,
    since: datetime | None = None,
) -> dict[str, int]:
    """Import historical WhatsApp chats from Evolution into ai_conversations."""
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)

    headers = _build_sync_headers(settings, tenant_id)
    chats = await _fetch_history_chats(instance_name, settings)
    supported = _filter_supported_chats(chats, max_chats)

    chat_results = [
        await _sync_one_chat(chat, instance_name, tenant_id, settings, headers, page_size, since)
        for chat in supported
    ]
    return {
        "chats_scanned": len(chat_results),
        "chats_imported": sum(1 for r in chat_results if r["status"] == "imported"),
        "chats_failed": sum(1 for r in chat_results if r["status"] == "failed"),
        "messages_imported": sum(r["imported"] for r in chat_results),
        "messages_skipped": sum(r["skipped"] for r in chat_results),
    }


async def _find_or_create_lead(
    phone: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    *,
    api_read_headers: dict[str, str],
    api_write_headers: dict[str, str],
) -> UUID | None:
    lead_id = await _search_lead(phone, tenant_id, settings, api_read_headers)
    if lead_id is not None:
        return lead_id
    return await _create_lead(phone, tenant_id, settings, api_write_headers)


async def _fetch_history_chats(instance_name: str, settings: CanalesSettings) -> list[dict[str, Any]]:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL, timeout=20.0)
    response = await client.post(
        f"/chat/findChats/{instance_name}",
        headers={"apikey": settings.EVOLUTION_API_KEY},
        json={},
    )
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, list) else []


async def _import_page_batch(
    records: list, since: datetime | None,
    tenant_id: UUID, lead_id: UUID,
    settings: CanalesSettings, auth_headers: dict[str, str],
) -> tuple[int, int]:
    """Normalize records and import a single page batch. Returns (imported, skipped)."""
    parsed = [_normalize_history_message(record, since) for record in records]
    normalized = [m for m in parsed if m is not None]
    skipped = len(parsed) - len(normalized)
    if not normalized:
        return 0, skipped
    result = await _import_historical_messages(
        tenant_id=tenant_id, lead_id=lead_id,
        messages=normalized, settings=settings, auth_headers=auth_headers,
    )
    return int(result.get("imported_count", 0)), skipped + int(result.get("skipped_count", 0))


def _is_valid_phone(phone: str | None) -> bool:
    """Check if phone string contains at least one digit."""
    return bool(phone and any(c.isdigit() for c in phone))


async def _paginate_history(
    instance_name: str, remote_jid: str, page_size: int,
    since: datetime | None, tenant_id: UUID, lead_id: UUID,
    settings: CanalesSettings, ai_import_headers: dict[str, str],
) -> list[tuple[int, int]]:
    """Fetch and import all pages of history for a single chat."""
    page_results: list[tuple[int, int]] = []
    page = 1
    while True:
        batch = await _fetch_history_messages(instance_name, remote_jid, page, page_size, settings)
        block = batch.get("messages", {})
        records = block.get("records", [])
        if not isinstance(records, list) or not records:
            break
        pg_imported, pg_skipped = await _import_page_batch(
            records, since, tenant_id, lead_id, settings, ai_import_headers,
        )
        page_results.append((pg_imported, pg_skipped))
        if page >= int(block.get("pages", page) or page):
            break
        page = page + 1
    return page_results


async def _sync_single_chat_history(
    remote_jid: str,
    instance_name: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    *,
    api_read_headers: dict[str, str],
    api_write_headers: dict[str, str],
    ai_import_headers: dict[str, str],
    page_size: int,
    since: datetime | None,
) -> dict[str, int]:
    phone = _normalize_phone(remote_jid)
    empty = {"messages_imported": 0, "messages_skipped": 0}
    if not _is_valid_phone(phone):
        return empty

    lead_id = await _find_or_create_lead(
        phone, tenant_id, settings,
        api_read_headers=api_read_headers, api_write_headers=api_write_headers,
    )
    if lead_id is None:
        logger.warning("Skipping history sync for %s — could not resolve lead", remote_jid)
        return empty

    page_results = await _paginate_history(
        instance_name, remote_jid, page_size, since,
        tenant_id, lead_id, settings, ai_import_headers,
    )
    return {
        "messages_imported": sum(r[0] for r in page_results),
        "messages_skipped": sum(r[1] for r in page_results),
    }


async def _fetch_history_messages(
    instance_name: str,
    remote_jid: str,
    page: int,
    page_size: int,
    settings: CanalesSettings,
) -> dict[str, Any]:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL, timeout=20.0)
    response = await client.post(
        f"/chat/findMessages/{instance_name}",
        headers={"apikey": settings.EVOLUTION_API_KEY},
        json={
            "where": {
                "key": {
                    "remoteJid": remote_jid,
                }
            },
            "page": page,
            "offset": page_size,
        },
    )
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, dict) else {}


async def _import_historical_messages(
    tenant_id: UUID,
    lead_id: UUID,
    messages: list[dict[str, str]],
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    response = await internal_http.post(
        f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/ai/conversations/import",
        headers=_tenant_headers(tenant_id, auth_headers),
        json={
            "lead_id": str(lead_id),
            "canal": "WHATSAPP",
            "messages": messages,
        },
        timeout=20.0,
    )
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, dict) else {}


async def _search_lead(
    phone: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> UUID | None:
    headers = _tenant_headers(tenant_id, auth_headers)
    try:
        response = await internal_http.get(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads?telefono={phone}&page_size=1",
            headers=headers,
        )
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to search lead by phone %s", phone)
        return None
    if response.status_code != 200:
        return None
    items = response.json().get("data", [])
    if not items:
        return None
    return UUID(items[0]["id"])


async def _create_lead(
    phone: str,
    tenant_id: UUID,
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> UUID | None:
    headers = _tenant_headers(tenant_id, auth_headers)
    payload = {"nombre": f"WhatsApp {phone}", "telefono": phone, "canal": "WHATSAPP"}
    try:
        response = await internal_http.post(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads",
            headers=headers, json=payload,
        )
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to create lead for phone %s", phone)
        return None
    if response.status_code in {200, 201}:
        lead_id = _extract_lead_id(response.json())
        return UUID(lead_id) if lead_id else None
    if response.status_code == 409:
        # Race condition: lead was created by a concurrent request, re-search
        logger.info("Lead create returned 409 for phone %s, re-searching", phone)
        return await _search_lead(phone, tenant_id, settings, auth_headers)
    return None


async def _progress_lead_estado(
    lead_id: UUID,
    tenant_id: UUID,
    settings: CanalesSettings,
    auth_headers: dict[str, str],
) -> None:
    """Advance lead estado from NUEVO to CONTACTADO after first AI reply.

    This is fire-and-forget — failures are logged but don't block the response.
    """
    headers = _tenant_headers(tenant_id, auth_headers)
    try:
        # First check current estado
        resp = await internal_http.get(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads/{lead_id}",
            headers=headers,
        )
        if resp.status_code != 200:
            return
        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        estado = (data.get("estado") or "").upper() if isinstance(data, dict) else ""
        if estado != "NUEVO":
            return
        # PATCH to CONTACTADO
        await internal_http.patch(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads/{lead_id}",
            headers=headers,
            json={"estado": "CONTACTADO"},
        )
        logger.info("Lead %s progressed NUEVO → CONTACTADO", lead_id)
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to progress lead %s estado", lead_id, exc_info=True)


async def _forward_to_ai(
    message: str,
    lead_id: UUID | None,
    tenant_id: UUID,
    settings: CanalesSettings,
    contact_id: str | None = None,
    media_url: str | None = None,
    media_type: str | None = None,
) -> dict | None:
    """Forward the message to the api_execute AI orchestrator.

    api_execute builds the full business context (prompt + knowledge + products),
    generates the reply via open_agent and persists the conversation.
    """
    orchestrator_headers = _service_headers(
        settings,
        tenant_id,
        audience="api_execute",
        scopes=("chat:write",),
    )
    payload: dict = {"message": message, "canal": "WHATSAPP"}
    if lead_id is not None:
        payload["lead_id"] = str(lead_id)
    if contact_id is not None:
        payload["contact_id"] = contact_id
    if media_url:
        payload["media_url"] = media_url
    if media_type:
        payload["media_type"] = media_type
    try:
        response = await internal_http.post(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/ai/process-message",
            json=payload,
            headers=_tenant_headers(tenant_id, orchestrator_headers),
            timeout=60.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Failed to forward message to api_execute orchestrator")
        return None
    return response.json()


async def _send_reply(
    reply_text: str,
    phone: str,
    instance_name: str,
    settings: CanalesSettings,
    lead_id: UUID | None,
) -> dict:
    if not reply_text:
        return _reply_result(lead_id)
    formatted = markdown_to_whatsapp(reply_text)
    await asyncio.sleep(random.uniform(_REPLY_DELAY_MIN, _REPLY_DELAY_MAX))
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            await send_message(phone, formatted, instance_name, settings)
            last_err = None
            break
        except (httpx.HTTPError, RuntimeError) as exc:
            last_err = exc
            if attempt < 2:
                await asyncio.sleep(0.4 * (attempt + 1))
    if last_err is not None:
        logger.exception("Failed to send WhatsApp reply to %s after 3 attempts", phone)
        return {
            "status": "partial",
            "reason": "reply_send_failed",
            "ai_response": formatted,
        }
    logger.info("Processed incoming WhatsApp from %s (lead=%s)", phone, lead_id)
    return _reply_result(lead_id)


def _reply_result(lead_id: UUID | None) -> dict:
    return {"status": "replied", "lead_id": str(lead_id) if lead_id else None}


def _tenant_headers(tenant_id: UUID, auth_headers: dict[str, str]) -> dict[str, str]:
    headers = dict(auth_headers)
    headers.setdefault("X-Tenant-ID", str(tenant_id))
    return headers


def _extract_lead_id(body: dict) -> str:
    direct_id = body.get("id", "")
    if direct_id:
        return direct_id
    data = body.get("data", {})
    if isinstance(data, dict):
        return data.get("id", "")
    return ""


def _is_supported_chat(remote_jid: str) -> bool:
    if not remote_jid or "@" not in remote_jid:
        return False
    return remote_jid not in {"status@broadcast"} and not remote_jid.endswith(
        ("@g.us", "@broadcast", "@newsletter", "@lid")
    )


def _normalize_history_message(record: dict[str, Any], since: datetime | None) -> dict[str, str] | None:
    if not isinstance(record, dict):
        return None

    key = record.get("key", {})
    if not isinstance(key, dict):
        return None

    text = extract_message_text(record.get("message"))
    created_at = _coerce_history_timestamp(record.get("messageTimestamp"))
    if not text or created_at is None:
        return None
    if since is not None and created_at < since:
        return None

    return {
        "role": "assistant" if key.get("fromMe") else "user",
        "content": text,
        "created_at": created_at.isoformat(),
    }


def _coerce_history_timestamp(raw_timestamp: Any) -> datetime | None:
    if raw_timestamp is None or isinstance(raw_timestamp, bool):
        return None

    try:
        value = float(raw_timestamp) if isinstance(raw_timestamp, str) else float(raw_timestamp)
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _list_response_text(message: dict[str, Any]) -> str:
    """Extract selected option from a WhatsApp interactive list response."""
    lrm = message.get("listResponseMessage")
    if not isinstance(lrm, dict):
        return ""
    title = lrm.get("title", "")
    if isinstance(title, str) and title.strip():
        return title.strip()
    reply = lrm.get("singleSelectReply", {})
    if isinstance(reply, dict):
        row_id = reply.get("selectedRowId", "")
        if isinstance(row_id, str) and row_id.strip():
            return row_id.replace("_", " ").strip()
    return ""


def _button_response_text(message: dict[str, Any]) -> str:
    """Extract selected option from a WhatsApp button response."""
    brm = message.get("buttonsResponseMessage")
    if not isinstance(brm, dict):
        return ""
    selected = brm.get("selectedDisplayText", "")
    if isinstance(selected, str) and selected.strip():
        return selected.strip()
    button_id = brm.get("selectedButtonId", "")
    if isinstance(button_id, str) and button_id.strip():
        return button_id.strip()
    return ""


def _extract_text(message: dict[str, Any]) -> str:
    for extractor in (
        _conversation_text,
        _extended_text,
        _list_response_text,
        _button_response_text,
        _caption_text,
    ):
        text = extractor(message)
        if text:
            return text
    return ""


def _normalize_message(message: Any) -> dict[str, Any]:
    if isinstance(message, str):
        return {"conversation": message}
    if not isinstance(message, dict):
        return {}

    current = message
    while True:
        nested = _wrapped_message(current)
        if nested is None:
            return current
        current = nested


def _wrapped_message(message: dict[str, Any]) -> dict[str, Any] | None:
    for key in MESSAGE_WRAPPER_KEYS:
        wrapper = message.get(key)
        if not isinstance(wrapper, dict):
            continue
        nested = wrapper.get("message")
        if isinstance(nested, dict):
            return nested
    return None


def _conversation_text(message: dict[str, Any]) -> str:
    conversation = message.get("conversation", "")
    return conversation.strip() if isinstance(conversation, str) else ""


def _extended_text(message: dict[str, Any]) -> str:
    return _nested_str(message, "extendedTextMessage", "text")


def _caption_text(message: dict[str, Any]) -> str:
    for key in ("imageMessage", "videoMessage", "documentMessage"):
        caption = _nested_str(message, key, "caption")
        if caption:
            return caption
    return ""


def _nested_str(message: dict[str, Any], key: str, field: str) -> str:
    nested = message.get(key)
    if not isinstance(nested, dict):
        return ""
    value = nested.get(field, "")
    return value.strip() if isinstance(value, str) else ""


def _enforce_send_rate_limit(instance_name: str) -> None:
    """Apply a local per-instance throttle to reduce WhatsApp ban risk."""
    now = time.monotonic()
    history = _instance_send_history.setdefault(instance_name, deque())
    while history and now - history[0] > _RATE_LIMIT_WINDOW_SECONDS:
        history.popleft()
    if len(history) >= _RATE_LIMIT_MAX_MESSAGES:
        raise RuntimeError("WhatsApp send rate limit exceeded for this instance")
    history.append(now)


# ── Send Presence ("typing…" indicator) ──────────────────────────────

async def send_presence(
    phone: str,
    instance_name: str,
    settings: CanalesSettings,
    presence: str = "composing",
    # Evolution's sendPresence RE-EMITS "composing" mid-flight when delay > 20000
    # (it loops composing → wait 20s → paused → composing …), so the typing bubble
    # reappears ~20s after a fast reply. Keep this at/below 20000 → a single
    # composing/paused pair is sent; _keep_composing() covers longer replies.
    delay_ms: int = 18_000,
) -> None:
    """Send presence state (composing/recording) to a WhatsApp contact."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL, timeout=10.0)
    headers = {"apikey": settings.EVOLUTION_API_KEY}
    payload = {
        "number": phone,
        "delay": delay_ms,
        "presence": presence,
    }
    try:
        resp = await client.post(
            f"/chat/sendPresence/{instance_name}",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        logger.debug("Presence '%s' sent to %s via %s", presence, phone, instance_name)
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to send presence to %s", phone, exc_info=True)


async def _keep_composing(
    phone: str,
    instance_name: str,
    settings: CanalesSettings,
    *,
    interval: float = _COMPOSING_REFRESH_SECONDS,
    max_refreshes: int = 8,
) -> None:
    """Keep the WhatsApp typing bubble alive during a slow reply.

    Re-sends the 'composing' presence every `interval` seconds (up to
    `max_refreshes` times) until cancelled; WhatsApp clients expire the typing
    indicator on their own after a few seconds without a refresh. The bound is a
    safety cap so a leaked task self-terminates instead of typing forever.
    """
    try:
        for _ in range(max_refreshes):
            await asyncio.sleep(interval)
            await send_presence(phone, instance_name, settings, "composing")
    except asyncio.CancelledError:
        pass


# ── Send Poll ────────────────────────────────────────────────────────

async def send_poll(
    phone: str,
    question: str,
    options: list[str],
    instance_name: str,
    settings: CanalesSettings,
    selectable_count: int = 1,
) -> dict:
    """Send a WhatsApp poll message via Evolution API."""
    _enforce_send_rate_limit(instance_name)
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    headers = {"apikey": settings.EVOLUTION_API_KEY}
    payload = {
        "number": phone,
        "name": question,
        "selectableCount": selectable_count,
        "values": options,
    }
    response = await client.post(
        f"/message/sendPoll/{instance_name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    logger.info("WhatsApp poll sent to %s via %s: %s", phone, instance_name, question)
    return response.json()


# ── Send List ────────────────────────────────────────────────────────

async def send_list(
    phone: str,
    title: str,
    description: str,
    button_text: str,
    sections: list[dict],
    instance_name: str,
    settings: CanalesSettings,
    footer_text: str = "",
) -> dict:
    """Send a WhatsApp list message via Evolution API.

    sections format: [{"title": "...", "rows": [{"title": "...", "description": "...", "rowId": "..."}]}]
    """
    _enforce_send_rate_limit(instance_name)
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    headers = {"apikey": settings.EVOLUTION_API_KEY}
    payload = {
        "number": phone,
        "title": title,
        "description": description,
        "buttonText": button_text,
        "footerText": footer_text,
        "sections": sections,
    }
    response = await client.post(
        f"/message/sendList/{instance_name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    logger.info("WhatsApp list sent to %s via %s: %s", phone, instance_name, title)
    return response.json()


# ── Debounce logic — accumulate consecutive messages ─────────────────

def _debounce_key(tenant_id: UUID, phone: str) -> tuple[str, str]:
    return (str(tenant_id), phone)


async def _flush_debounce_buffer(
    key: tuple[str, str],
    settings: CanalesSettings,
) -> None:
    """Timer callback: merge buffered messages and process as one."""
    async with _debounce_lock:
        entry = _debounce_buffers.pop(key, None)
    if entry is None:
        return

    messages = entry["messages"]
    first_data = entry["first_data"]
    session_factory = entry["session_factory"]

    merged_text = "\n".join(m for m in messages if m)
    first_data["message"] = merged_text
    logger.info(
        "Debounce flush: tenant=%s phone=%s msgs=%d merged_len=%d",
        key[0], key[1], len(messages), len(merged_text),
    )

    async with session_factory() as db:
        try:
            from shared.database.session import set_instance_lookup_context
            await set_instance_lookup_context(db, first_data["instance_name"])
            await process_incoming(first_data, settings, db, _skip_debounce=True)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error processing debounced messages for %s", key)


async def _enqueue_debounce(
    data: dict,
    message_text: str,
    tenant_id: UUID,
    phone: str,
    debounce_seconds: float,
    settings: CanalesSettings,
    session_factory: Any,
) -> bool:
    """Add message to debounce buffer. Returns True if buffered (caller should skip processing)."""
    key = _debounce_key(tenant_id, phone)
    loop = asyncio.get_running_loop()

    async with _debounce_lock:
        existing = _debounce_buffers.get(key)
        if existing is not None:
            # Cancel existing timer, add message, restart timer
            if existing.get("timer_task") and not existing["timer_task"].done():
                existing["timer_task"].cancel()
            existing["messages"].append(message_text)
            existing["timer_task"] = asyncio.create_task(
                _debounce_timer(key, debounce_seconds, settings)
            )
            logger.debug("Debounce: appended msg #%d for %s", len(existing["messages"]), key)
            return True

        # First message — start new buffer
        entry = {
            "messages": [message_text],
            "first_data": dict(data),
            "session_factory": session_factory,
            "timer_task": asyncio.create_task(
                _debounce_timer(key, debounce_seconds, settings)
            ),
        }
        _debounce_buffers[key] = entry
        logger.debug("Debounce: started buffer for %s (%.1fs)", key, debounce_seconds)
        return True


async def _debounce_timer(
    key: tuple[str, str],
    seconds: float,
    settings: CanalesSettings,
) -> None:
    """Wait for debounce window then flush."""
    try:
        await asyncio.sleep(seconds)
        await _flush_debounce_buffer(key, settings)
    except asyncio.CancelledError:
        pass
