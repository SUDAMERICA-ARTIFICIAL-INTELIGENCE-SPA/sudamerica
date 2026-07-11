"""Notify customers via WhatsApp for reservation events (confirmation + reminders)."""

import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ApiExecuteSettings
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)


async def notify_reservation_confirmed(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    telefono: str,
    nombre_cliente: str,
    fecha: str,
    hora: str,
    cantidad_personas: int,
) -> None:
    """Send a WhatsApp message to confirm a reservation."""
    message = (
        f"¡Hola {nombre_cliente}! Tu reserva ha sido confirmada.\n\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora}\n"
        f"Personas: {cantidad_personas}\n\n"
        f"¡Te esperamos!"
    )

    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="canales_service",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("whatsapp:send",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    try:
        resp = await internal_http.post(
            f"{settings.SERVICE_CANALES_URL}/api/v1/canales/whatsapp/send",
            json={"to": telefono, "message": message, "tenant_id": str(tenant_id)},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        logger.info("Reservation confirmation sent to %s (tenant %s)", telefono, tenant_id)
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to send reservation confirmation to %s", telefono, exc_info=True)


async def _send_whatsapp(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    telefono: str,
    message: str,
) -> bool:
    """Send a WhatsApp message via canales_service. Returns True on success."""
    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="canales_service",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("whatsapp:send",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    try:
        resp = await internal_http.post(
            f"{settings.SERVICE_CANALES_URL}/api/v1/canales/whatsapp/send",
            json={"to": telefono, "message": message, "tenant_id": str(tenant_id)},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        return True
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Failed to send WhatsApp to %s", telefono, exc_info=True)
        return False


async def send_reservation_reminders(
    settings: ApiExecuteSettings,
    db: AsyncSession,
    hours_ahead: int = 2,
) -> dict:
    """Send WhatsApp reminders for reservations happening within `hours_ahead`.

    Returns summary of sent/failed counts.
    Prevents double-sends by checking `recordatorio_enviado` flag.
    """
    now = datetime.now(timezone.utc)
    target_start = now + timedelta(hours=max(0, hours_ahead - 1))
    target_end = now + timedelta(hours=hours_ahead + 1)
    today = now.date()

    # Find confirmed reservations in the reminder window, not yet reminded
    sql = text("""
        SELECT id, tenant_id, nombre_cliente, telefono, fecha_reserva,
               hora_inicio, cantidad_personas
        FROM reservaciones
        WHERE activo = true
          AND estado IN ('CONFIRMADA', 'PENDIENTE')
          AND fecha_reserva = :fecha
          AND telefono IS NOT NULL
          AND telefono != ''
          AND COALESCE(recordatorio_enviado, false) = false
        ORDER BY hora_inicio
    """)
    result = await db.execute(sql, {"fecha": today})
    rows = result.mappings().all()

    sent = 0
    failed = 0

    for row in rows:
        # Check if reservation time falls within reminder window
        reservation_dt = datetime.combine(
            row["fecha_reserva"],
            row["hora_inicio"],
            tzinfo=timezone.utc,
        )
        if not (target_start <= reservation_dt <= target_end):
            continue

        hora_str = row["hora_inicio"].strftime("%H:%M") if hasattr(row["hora_inicio"], "strftime") else str(row["hora_inicio"])
        message = (
            f"¡Hola {row['nombre_cliente']}! Te recordamos tu reserva para hoy.\n\n"
            f"Hora: {hora_str}\n"
            f"Personas: {row['cantidad_personas']}\n\n"
            f"¿Confirmas tu asistencia? Responde SI para confirmar o NO para cancelar."
        )

        tid = row["tenant_id"] if isinstance(row["tenant_id"], UUID) else UUID(str(row["tenant_id"]))
        ok = await _send_whatsapp(settings, tid, row["telefono"], message)

        if ok:
            # Mark as reminded to prevent duplicates
            await db.execute(
                text("UPDATE reservaciones SET recordatorio_enviado = true WHERE id = :rid"),
                {"rid": str(row["id"])},
            )
            sent += 1
        else:
            failed += 1

    await db.commit()
    logger.info("Reservation reminders: %d sent, %d failed", sent, failed)
    return {"sent": sent, "failed": failed, "total_candidates": len(rows)}
