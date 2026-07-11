"""Business logic for the human-review (revision humana) panel."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import CallbackSettings
from shared.models.enums import RevisionAccion, RevisionDeliveryStatus
from shared.middleware import build_service_auth_headers
from shared.schemas import PaginatedResponse, PaginationParams
from shared.utils import ConflictError, NotFoundError
from shared.utils.http_client import internal_http

from app.models.revision_humana import RevisionHumana
from app.schemas.revision import RevisionCreate, RevisionResponse, RevisionStats

logger = logging.getLogger(__name__)
REVISION_CLAIM_TTL = timedelta(minutes=5)


async def create_revision(
    session: AsyncSession,
    tenant_id: UUID,
    data: RevisionCreate,
    settings: CallbackSettings | None = None,
) -> RevisionHumana:
    """Enqueue a new AI response for human review."""
    if data.lead_id and settings and not await _lead_exists(settings, tenant_id, data.lead_id):
        raise NotFoundError("Lead", str(data.lead_id))

    revision = RevisionHumana(
        tenant_id=tenant_id,
        lead_id=data.lead_id,
        mensaje_original=data.mensaje_original,
        respuesta_ia=data.respuesta_ia,
        confianza=data.confianza,
    )
    session.add(revision)
    await session.flush()
    return revision


async def list_pendientes(
    session: AsyncSession,
    tenant_id: UUID,
    pagination: PaginationParams,
) -> PaginatedResponse[RevisionResponse]:
    """Return paginated list of pending (unprocessed) reviews."""
    base = select(RevisionHumana).where(
        RevisionHumana.tenant_id == tenant_id,
        RevisionHumana.procesado.is_(False),
        RevisionHumana.activo.is_(True),
    )
    total = await _count(session, base)
    rows = await session.scalars(
        base.order_by(RevisionHumana.created_at.asc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    items = [RevisionResponse.model_validate(r) for r in rows.all()]
    return PaginatedResponse.build(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def aprobar(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    operador_id: UUID,
    tiempo_ms: int,
    settings: CallbackSettings,
) -> RevisionHumana:
    """Approve the AI response and forward it to the tasks service."""
    revision = await _claim_revision(session, tenant_id, revision_id, operador_id)

    try:
        await _notify_tasks(
            settings=settings,
            tenant_id=tenant_id,
            revision_id=revision.id,
            lead_id=revision.lead_id,
            respuesta=revision.respuesta_ia,
        )
    except ConflictError:
        await _release_revision_claim(session, revision)
        raise
    except RuntimeError as exc:
        await _record_delivery_failure(session, revision, str(exc))
        raise

    revision.accion = RevisionAccion.APROBAR.value
    revision.operador_id = operador_id
    revision.procesado = True
    revision.tiempo_revision_ms = tiempo_ms
    revision.delivery_error = None
    await session.commit()
    await session.refresh(revision)
    return revision


async def editar(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    operador_id: UUID,
    respuesta_editada: str,
    tiempo_ms: int,
    settings: CallbackSettings,
) -> RevisionHumana:
    """Edit the AI response and forward the corrected version."""
    revision = await _claim_revision(session, tenant_id, revision_id, operador_id)

    try:
        await _notify_tasks(
            settings=settings,
            tenant_id=tenant_id,
            revision_id=revision.id,
            lead_id=revision.lead_id,
            respuesta=respuesta_editada,
        )
    except ConflictError:
        await _release_revision_claim(session, revision)
        raise
    except RuntimeError as exc:
        await _record_delivery_failure(session, revision, str(exc))
        raise

    revision.accion = RevisionAccion.EDITAR.value
    revision.respuesta_editada = respuesta_editada
    revision.operador_id = operador_id
    revision.procesado = True
    revision.tiempo_revision_ms = tiempo_ms
    revision.delivery_error = None
    await session.commit()
    await session.refresh(revision)
    return revision


async def rechazar(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    operador_id: UUID,
    tiempo_ms: int,
) -> RevisionHumana:
    """Reject the AI response; no message is sent."""
    revision = await _claim_revision(session, tenant_id, revision_id, operador_id)

    revision.accion = RevisionAccion.RECHAZAR.value
    revision.operador_id = operador_id
    revision.procesado = True
    revision.tiempo_revision_ms = tiempo_ms
    revision.delivery_status = RevisionDeliveryStatus.SKIPPED.value
    revision.delivery_timestamp = datetime.now(timezone.utc)
    revision.delivery_error = None
    await session.commit()
    await session.refresh(revision)
    return revision


async def get_stats(
    session: AsyncSession,
    tenant_id: UUID,
) -> RevisionStats:
    """Return aggregated review statistics for today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    base = select(RevisionHumana).where(
        RevisionHumana.tenant_id == tenant_id,
        RevisionHumana.activo.is_(True),
    )
    total_pendientes = await _count(
        session, base.where(RevisionHumana.procesado.is_(False))
    )
    today_filter = base.where(RevisionHumana.updated_at >= today_start)
    aprobadas = await _count_accion(session, today_filter, RevisionAccion.APROBAR)
    editadas = await _count_accion(session, today_filter, RevisionAccion.EDITAR)
    rechazadas = await _count_accion(session, today_filter, RevisionAccion.RECHAZAR)
    tiempo = await _avg_tiempo(session, today_filter)
    precision = await _calc_precision(session, today_filter, aprobadas, editadas, rechazadas)
    return RevisionStats(
        total_pendientes=total_pendientes,
        aprobadas_hoy=aprobadas,
        editadas_hoy=editadas,
        rechazadas_hoy=rechazadas,
        tiempo_promedio_ms=tiempo,
        precision_ia=precision,
    )


def _diagnose_claim_failure(revision: RevisionHumana) -> str:
    """Return an error message explaining why a revision cannot be claimed."""
    if revision.procesado:
        return "Revision already processed"
    _STATUS_ERRORS = {
        RevisionDeliveryStatus.SENT.value: "Revision already delivered",
        RevisionDeliveryStatus.SKIPPED.value: "Revision already rejected",
        RevisionDeliveryStatus.PROCESSING.value: "Revision delivery already in progress",
    }
    msg = _STATUS_ERRORS.get(revision.delivery_status)
    if msg:
        return msg
    if revision.operador_id is not None and not _claim_is_stale(revision.updated_at):
        return "Revision already being processed"
    return "Revision is not available for processing"


async def _try_claim_update(
    session: AsyncSession, tenant_id: UUID, revision_id: UUID,
    operador_id: UUID, claim_started_at: datetime,
) -> bool:
    """Attempt atomic UPDATE claim. Returns True if successful."""
    stale_before = claim_started_at - REVISION_CLAIM_TTL
    claimed = await session.execute(
        update(RevisionHumana)
        .where(
            RevisionHumana.id == revision_id,
            RevisionHumana.tenant_id == tenant_id,
            RevisionHumana.activo.is_(True),
            RevisionHumana.procesado.is_(False),
            or_(
                RevisionHumana.operador_id.is_(None),
                RevisionHumana.updated_at < stale_before,
            ),
            RevisionHumana.delivery_status.in_(
                [RevisionDeliveryStatus.PENDING.value, RevisionDeliveryStatus.FAILED.value]
            ),
        )
        .values(operador_id=operador_id, updated_at=claim_started_at)
        .returning(RevisionHumana.id)
    )
    return claimed.first() is not None


async def _claim_revision(
    session: AsyncSession,
    tenant_id: UUID,
    revision_id: UUID,
    operador_id: UUID,
) -> RevisionHumana:
    """Claim a pending revision before any operator action is applied."""
    claim_started_at = datetime.now(timezone.utc)
    if await _try_claim_update(session, tenant_id, revision_id, operador_id, claim_started_at):
        await session.commit()
        return await _get_revision(session, tenant_id, revision_id)

    revision = await _get_revision(session, tenant_id, revision_id)
    raise ConflictError(_diagnose_claim_failure(revision))


async def _release_revision_claim(
    session: AsyncSession,
    revision: RevisionHumana,
) -> None:
    """Return a claimed revision to the pending queue."""
    if revision.procesado:
        return
    revision.operador_id = None
    await session.commit()
    await session.refresh(revision)


async def _get_revision(
    session: AsyncSession, tenant_id: UUID, revision_id: UUID
) -> RevisionHumana:
    """Fetch a single revision or raise NotFoundError."""
    stmt = select(RevisionHumana).where(
        RevisionHumana.id == revision_id,
        RevisionHumana.tenant_id == tenant_id,
        RevisionHumana.activo.is_(True),
    )
    revision = await session.scalar(stmt)
    if not revision:
        raise NotFoundError("RevisionHumana", str(revision_id))
    return revision


async def _count(session: AsyncSession, stmt) -> int:
    """Count rows for a given select statement."""
    count_stmt = select(func.count()).select_from(stmt.subquery())
    result = await session.scalar(count_stmt)
    return result or 0


async def _count_accion(session: AsyncSession, base_stmt, accion: RevisionAccion) -> int:
    """Count rows matching a specific accion value."""
    return await _count(
        session,
        base_stmt.where(
            RevisionHumana.accion == accion.value,
            RevisionHumana.procesado.is_(True),
        ),
    )


async def _avg_tiempo(session: AsyncSession, base_stmt) -> float | None:
    """Average review time for processed revisions."""
    processed = base_stmt.where(RevisionHumana.procesado.is_(True)).subquery()
    stmt = select(func.avg(processed.c.tiempo_revision_ms))
    result = await session.scalar(stmt)
    return float(result) if result is not None else None


async def _calc_precision(
    session: AsyncSession,
    base_stmt,
    aprobadas: int,
    editadas: int,
    rechazadas: int,
) -> float:
    """Calculate AI precision: approved / total processed."""
    total_processed = aprobadas + editadas + rechazadas
    if total_processed == 0:
        return 0.0
    return round(aprobadas / total_processed, 4)


async def _notify_tasks(
    settings: CallbackSettings,
    tenant_id: UUID,
    revision_id: UUID,
    lead_id: UUID | None,
    respuesta: str,
) -> None:
    """Send the approved/edited response to the tasks service."""
    body = {
        "revision_id": str(revision_id),
        "lead_id": str(lead_id) if lead_id else None,
        "respuesta": respuesta,
    }
    headers = build_service_auth_headers(
        service_name="callback_manual",
        audience="tasks",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("tasks:send_response",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    try:
        response = await internal_http.post(
            f"{settings.SERVICE_TASKS_URL}/api/v1/tasks/send-response",
            json=body, headers=headers,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _extract_error_detail(exc.response)
        if exc.response.status_code == 409:
            raise ConflictError(detail or "Delivery already in progress") from exc
        logger.exception("Failed to notify tasks service for revision %s", revision_id)
        raise RuntimeError(detail or "Tasks service unavailable") from exc
    except httpx.HTTPError as exc:
        logger.exception("Failed to notify tasks service for revision %s", revision_id)
        raise RuntimeError("Tasks service unavailable") from exc

    payload = response.json()
    if not payload.get("success"):
        detail = payload.get("detail") or "Tasks service rejected delivery"
        raise RuntimeError(str(detail))


async def _record_delivery_failure(
    session: AsyncSession,
    revision: RevisionHumana,
    detail: str,
) -> None:
    """Persist failed delivery attempts while keeping the review pending."""
    revision.operador_id = None
    revision.delivery_status = RevisionDeliveryStatus.FAILED.value
    revision.delivery_timestamp = datetime.now(timezone.utc)
    revision.delivery_error = detail
    await session.commit()
    await session.refresh(revision)


def _claim_is_stale(updated_at: datetime) -> bool:
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return updated_at < datetime.now(timezone.utc) - REVISION_CLAIM_TTL


def _extract_error_detail(response: httpx.Response) -> str | None:
    """Read the most useful detail field from an error response."""
    try:
        payload = response.json()
    except ValueError:
        return response.text or None
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return None


async def _lead_exists(settings: CallbackSettings, tenant_id: UUID, lead_id: UUID) -> bool:
    """Check lead existence via api_execute (respects domain boundaries)."""
    headers = build_service_auth_headers(
        service_name="callback_manual",
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
        return resp.status_code == 200
    except httpx.HTTPError:
        logger.warning("Could not verify lead %s via api_execute", lead_id)
        return True  # fail-open: don't block revision creation on network issues
