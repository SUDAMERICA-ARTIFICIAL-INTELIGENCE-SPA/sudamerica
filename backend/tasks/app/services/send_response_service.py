"""Service to deliver approved/edited AI responses to the lead."""

import logging
from uuid import UUID

import aiosmtplib
import httpx
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import TasksSettings
from app.models.task_log import TaskEstado, TaskLog, TaskTipo
from app.services import email_service
from shared.middleware import build_service_auth_headers
from shared.models.enums import RevisionDeliveryStatus
from shared.utils import ConflictError, NotFoundError
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)


async def _fetch_lead(
    settings: TasksSettings,
    tenant_id: UUID,
    lead_id: UUID,
) -> dict | None:
    """Lookup lead contact info via api_execute (respects domain boundaries)."""
    headers = build_service_auth_headers(
        service_name="tasks",
        audience="api_execute",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("leads:read",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    try:
        resp = await internal_http.get(
            f"{settings.SERVICE_API_EXECUTE_URL}/api/v1/core/leads/{lead_id}",
            headers=headers,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "nombre": data.get("nombre"),
            "email": data.get("email"),
            "telefono": data.get("telefono"),
            "canal": data.get("canal"),
        }
    except httpx.HTTPError:
        logger.warning("Could not fetch lead %s from api_execute", lead_id)
        return None


async def _log_task(
    session: AsyncSession,
    tenant_id: UUID,
    tipo: str,
    destinatario: str,
    contenido: str,
    estado: str,
    error_detail: str | None = None,
) -> TaskLog:
    """Create an audit log entry for the delivery attempt."""
    log = TaskLog(
        tenant_id=tenant_id,
        tipo=tipo,
        destinatario=destinatario,
        contenido=contenido,
        estado=estado,
        error_detail=error_detail,
    )
    session.add(log)
    await session.flush()
    return log


async def _fail_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    respuesta: str | None,
    destinatario: str,
    error_detail: str,
) -> dict:
    """Log failure and mark revision as failed. Returns a failure result dict."""
    await _log_task(
        session, tenant_id, TaskTipo.EMAIL, destinatario,
        respuesta, TaskEstado.FALLIDO, error_detail,
    )
    await _mark_revision_delivery(
        session, tenant_id, revision_id,
        RevisionDeliveryStatus.FAILED.value, error_detail,
    )
    return {"success": False, "canal": None, "detail": error_detail}


async def _mark_delivery_result(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    result: dict,
) -> None:
    """Mark revision delivery status based on a channel result dict."""
    status = (
        RevisionDeliveryStatus.SENT.value
        if result["success"]
        else RevisionDeliveryStatus.FAILED.value
    )
    error = None if result["success"] else result.get("detail")
    await _mark_revision_delivery(session, tenant_id, revision_id, status, error)


async def deliver_response(
    session: AsyncSession,
    tenant_id: UUID,
    lead_id: UUID | None,
    respuesta: str | None,
    revision_id: UUID,
    settings: TasksSettings,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Route the approved response (text and/or media) to the lead via the best channel."""
    await _claim_revision_delivery(session, tenant_id, revision_id)

    if not lead_id:
        logger.warning("send-response called without lead_id, revision=%s", revision_id)
        return await _fail_delivery(
            session, tenant_id, revision_id, respuesta, "unknown", "No lead_id provided",
        )

    lead = await _fetch_lead(settings, tenant_id, lead_id)
    if not lead:
        logger.warning("Lead %s not found for tenant %s", lead_id, tenant_id)
        return await _fail_delivery(
            session, tenant_id, revision_id, respuesta, str(lead_id), "Lead not found",
        )

    canal = (lead.get("canal") or "").upper()
    nombre = lead.get("nombre", "")

    result = await _route_delivery(
        session, tenant_id, lead, canal, nombre, respuesta, settings,
        media_url=media_url, media_type=media_type,
        file_name=file_name, caption=caption, mimetype=mimetype,
    )
    if result is not None:
        await _mark_delivery_result(session, tenant_id, revision_id, result)
        return result

    return await _fail_delivery(
        session, tenant_id, revision_id, respuesta, nombre, "No contact info available",
    )


async def _route_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    lead: dict,
    canal: str,
    nombre: str,
    respuesta: str | None,
    settings: TasksSettings,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict | None:
    """Try WhatsApp then email; return result dict or None if no contact info."""
    if canal == "WHATSAPP" and lead.get("telefono"):
        wa_result = await _send_via_whatsapp(
            session, tenant_id, lead["telefono"], nombre, respuesta, settings,
            media_url=media_url, media_type=media_type,
            file_name=file_name, caption=caption, mimetype=mimetype,
        )
        if wa_result["success"]:
            return wa_result
        if lead.get("email"):
            logger.warning("WhatsApp failed, attempting email fallback")
            return await _send_via_email(
                session, tenant_id, lead["email"], nombre, respuesta, settings,
            )
        return wa_result

    if lead.get("email"):
        return await _send_via_email(
            session, tenant_id, lead["email"], nombre, respuesta, settings,
        )
    return None


async def _send_via_email(
    session: AsyncSession,
    tenant_id: UUID,
    email_addr: str,
    nombre: str,
    respuesta: str,
    settings: TasksSettings,
) -> dict:
    """Deliver response via SMTP email."""
    try:
        result = await email_service.send_email(
            to=email_addr,
            subject=f"Respuesta para {nombre}" if nombre else "Respuesta a tu consulta",
            body=respuesta,
            html=None,
            settings=settings,
        )
        await _log_task(
            session,
            tenant_id,
            TaskTipo.EMAIL,
            email_addr,
            respuesta,
            TaskEstado.ENVIADO,
        )
        return {"success": True, "canal": "EMAIL", "detail": result.get("message_id")}
    except (aiosmtplib.SMTPException, OSError, ValueError) as exc:
        logger.error("Email delivery failed to %s: %s", email_addr, exc)
        await _log_task(
            session,
            tenant_id,
            TaskTipo.EMAIL,
            email_addr,
            respuesta,
            TaskEstado.FALLIDO,
            str(exc),
        )
        return {"success": False, "canal": "EMAIL", "detail": str(exc)}


def _build_whatsapp_payload(
    tenant_id: UUID,
    telefono: str,
    respuesta: str | None,
    content_log: str,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Build the WhatsApp send payload with optional media fields."""
    payload: dict = {"tenant_id": str(tenant_id), "to": telefono}
    _optional = {
        "message": respuesta, "media_url": media_url, "media_type": media_type,
        "file_name": file_name, "caption": caption, "mimetype": mimetype,
    }
    for key, value in _optional.items():
        if value:
            payload[key] = value
    if not payload.get("message") and not payload.get("media_url"):
        payload["message"] = content_log
    return payload


async def _send_via_whatsapp(
    session: AsyncSession,
    tenant_id: UUID,
    telefono: str,
    nombre: str,
    respuesta: str | None,
    settings: TasksSettings,
    *,
    media_url: str | None = None,
    media_type: str | None = None,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Deliver response (text and/or media) via canales service (Evolution API / WhatsApp)."""
    del nombre
    canales_url = getattr(settings, "SERVICE_CANALES_URL", "")
    content_log = respuesta or caption or f"[{(media_type or 'media').upper()}]"
    if not canales_url:
        logger.warning("SERVICE_CANALES_URL not configured, falling back to log only")
        await _log_task(
            session, tenant_id, TaskTipo.WHATSAPP, telefono,
            content_log, TaskEstado.FALLIDO, "Canales service URL not configured",
        )
        return {"success": False, "canal": "WHATSAPP", "detail": "Canales service not configured"}

    try:
        headers = build_service_auth_headers(
            service_name="tasks", audience="canales_service",
            tenant_id=tenant_id, secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM, scopes=("whatsapp:send",),
            expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
        )
        payload = _build_whatsapp_payload(
            tenant_id, telefono, respuesta, content_log,
            media_url=media_url, media_type=media_type,
            file_name=file_name, caption=caption, mimetype=mimetype,
        )
        resp = await internal_http.post(
            f"{canales_url}/api/v1/canales/whatsapp/send",
            json=payload, headers=headers,
        )
        resp.raise_for_status()
        await _log_task(
            session, tenant_id, TaskTipo.WHATSAPP, telefono,
            content_log, TaskEstado.ENVIADO,
        )
        return {"success": True, "canal": "WHATSAPP", "detail": None}
    except (httpx.HTTPError, RuntimeError) as exc:
        logger.error("WhatsApp delivery failed to %s: %s", telefono, exc)
        await _log_task(
            session, tenant_id, TaskTipo.WHATSAPP, telefono,
            content_log, TaskEstado.FALLIDO, str(exc),
        )
        return {"success": False, "canal": "WHATSAPP", "detail": str(exc)}


async def _try_claim_delivery_update(
    session: AsyncSession, tenant_id: UUID, revision_id: UUID,
) -> bool:
    """Attempt atomic UPDATE to claim delivery. Returns True if successful."""
    claimed = await session.execute(
        sql_text(
            """
            UPDATE revision_humana
            SET delivery_status = :processing,
                delivery_error = NULL,
                delivery_timestamp = NULL
            WHERE id = :rid
              AND tenant_id = :tid
              AND activo = true
              AND delivery_status NOT IN (:processing, :sent, :skipped)
            RETURNING id
            """
        ),
        {
            "rid": str(revision_id),
            "tid": str(tenant_id),
            "processing": RevisionDeliveryStatus.PROCESSING.value,
            "sent": RevisionDeliveryStatus.SENT.value,
            "skipped": RevisionDeliveryStatus.SKIPPED.value,
        },
    )
    return claimed.first() is not None


def _diagnose_delivery_claim_failure(current_status: str | None, revision_id: str) -> None:
    """Raise the appropriate error for a failed delivery claim."""
    if current_status is None:
        raise NotFoundError("RevisionHumana", revision_id)
    _STATUS_ERRORS = {
        RevisionDeliveryStatus.SENT.value: "Revision already delivered",
        RevisionDeliveryStatus.PROCESSING.value: "Revision delivery already in progress",
        RevisionDeliveryStatus.SKIPPED.value: "Revision was rejected and cannot be delivered",
    }
    raise ConflictError(_STATUS_ERRORS.get(current_status, "Revision delivery cannot be claimed"))


async def _fetch_current_delivery_status(
    session: AsyncSession, tenant_id: UUID, revision_id: UUID,
) -> str | None:
    """Fetch current delivery_status for a revision."""
    current = await session.execute(
        sql_text(
            "SELECT delivery_status FROM revision_humana "
            "WHERE id = :rid AND tenant_id = :tid AND activo = true"
        ),
        {"rid": str(revision_id), "tid": str(tenant_id)},
    )
    return current.scalar_one_or_none()


async def _claim_revision_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
) -> None:
    """Atomically claim a revision before attempting delivery."""
    if await _try_claim_delivery_update(session, tenant_id, revision_id):
        await session.flush()
        return

    current_status = await _fetch_current_delivery_status(session, tenant_id, revision_id)
    _diagnose_delivery_claim_failure(current_status, str(revision_id))


async def retry_failed_deliveries(
    session: AsyncSession,
    tenant_id: UUID,
    settings: TasksSettings,
    max_retries: int = 10,
) -> dict:
    """Re-attempt delivery for all FAILED revisions in the tenant.

    Returns summary of retry results.
    """
    result = await session.execute(
        sql_text(
            """
            SELECT id, lead_id, COALESCE(respuesta_editada, respuesta_ia) AS respuesta
            FROM revision_humana
            WHERE tenant_id = :tid
              AND activo = true
              AND delivery_status = :failed
              AND procesado = true
            ORDER BY created_at ASC
            LIMIT :limit
            """
        ),
        {
            "tid": str(tenant_id),
            "failed": RevisionDeliveryStatus.FAILED.value,
            "limit": max_retries,
        },
    )
    rows = result.mappings().all()
    outcomes = [await _retry_single_delivery(session, tenant_id, row, settings) for row in rows]

    retried = outcomes.count("succeeded") + outcomes.count("failed")
    succeeded = outcomes.count("succeeded")
    still_failed = outcomes.count("failed")

    if retried > 0:
        await session.commit()

    logger.info(
        "Retry failed deliveries: tenant=%s retried=%d succeeded=%d failed=%d",
        tenant_id, retried, succeeded, still_failed,
    )
    return {
        "retried": retried,
        "succeeded": succeeded,
        "still_failed": still_failed,
    }


async def _retry_single_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    row,
    settings: TasksSettings,
) -> str:
    """Retry a single failed delivery. Returns 'succeeded', 'failed', or 'skipped'."""
    revision_id = row["id"]
    lead_id = row["lead_id"]
    respuesta = row["respuesta"]

    await session.execute(
        sql_text(
            """
            UPDATE revision_humana
            SET delivery_status = :pending,
                delivery_error = NULL,
                delivery_timestamp = NULL
            WHERE id = :rid AND tenant_id = :tid
            """
        ),
        {
            "rid": str(revision_id),
            "tid": str(tenant_id),
            "pending": RevisionDeliveryStatus.PENDING.value,
        },
    )
    await session.flush()

    try:
        delivery = await deliver_response(
            session, tenant_id, lead_id, respuesta, revision_id, settings,
        )
        return "succeeded" if delivery.get("success") else "failed"
    except (ConflictError, NotFoundError):
        return "failed"


async def _mark_revision_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    status: str,
    error_detail: str | None,
) -> None:
    """Persist the latest delivery status back to revision_humana."""
    await session.execute(
        sql_text(
            """
            UPDATE revision_humana
            SET delivery_status = :status,
                delivery_timestamp = CURRENT_TIMESTAMP,
                delivery_error = :error_detail
            WHERE id = :rid AND tenant_id = :tid AND activo = true
            """
        ),
        {
            "rid": str(revision_id),
            "tid": str(tenant_id),
            "status": status,
            "error_detail": error_detail,
        },
    )
