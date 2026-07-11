"""Loyalty outreach — sends WhatsApp messages to at-risk loyal customers."""

import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ApiExecuteSettings
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)

# Message templates per loyalty tier
_TEMPLATES = {
    "VIP": (
        "¡Hola {nombre}! Te extrañamos en {restaurante}. "
        "Como cliente VIP, queremos invitarte a probar nuestras novedades. "
        "{favorito_line}"
        "¡Te esperamos pronto!"
    ),
    "FRECUENTE": (
        "¡Hola {nombre}! Hace tiempo que no nos visitas en {restaurante}. "
        "{favorito_line}"
        "¡Ven a vernos, te esperamos!"
    ),
}


def _build_message(
    nombre: str,
    estado_cliente: str,
    plato_favorito: str | None,
    restaurante: str,
) -> str:
    """Build a personalized outreach message."""
    template = _TEMPLATES.get(estado_cliente, _TEMPLATES["FRECUENTE"])
    favorito_line = (
        f"Tu favorito, {plato_favorito}, sigue en la carta. "
        if plato_favorito
        else ""
    )
    return template.format(
        nombre=nombre or "cliente",
        restaurante=restaurante,
        favorito_line=favorito_line,
    )


async def _fetch_restaurant_name(db: AsyncSession, tenant_id: UUID) -> str:
    """Fetch the restaurant/tenant name."""
    tenant_q = await db.execute(
        text("SELECT nombre FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    return tenant_q.scalar() or "nuestro restaurante"


async def _fetch_at_risk_customers(
    db: AsyncSession, tenant_id: UUID, limit: int,
) -> list:
    """Fetch VIP/FRECUENTE customers with phone numbers, ordered by spend."""
    sql = text("""
        SELECT id, nombre, telefono, estado_cliente, plato_favorito,
               ultima_visita, frecuencia_dias
        FROM leads
        WHERE tenant_id = :tid
          AND activo = true
          AND estado_cliente IN ('VIP', 'FRECUENTE')
          AND telefono IS NOT NULL
          AND telefono != ''
          AND frecuencia_dias > 0
          AND ultima_visita IS NOT NULL
        ORDER BY total_gastado DESC
        LIMIT :max_msgs
    """)
    result = await db.execute(sql, {"tid": str(tenant_id), "max_msgs": limit})
    return result.mappings().all()


def _is_overdue(row, now: datetime) -> tuple[bool, int]:
    """Check if a customer is overdue. Returns (is_overdue, days_since)."""
    try:
        ultima = row["ultima_visita"]
        days_since = (now.date() - (ultima.date() if hasattr(ultima, "date") else ultima)).days
    except (TypeError, AttributeError):
        return False, 0
    threshold = int(row["frecuencia_dias"] * 1.5)
    return days_since > threshold, days_since


async def _send_outreach_to_row(
    settings: ApiExecuteSettings, tenant_id: UUID,
    row, restaurante: str, now: datetime,
) -> str:
    """Process a single customer row. Returns 'sent', 'skip', or 'not_overdue'."""
    overdue, days_since = _is_overdue(row, now)
    if not overdue:
        return "not_overdue"
    message = _build_message(row["nombre"], row["estado_cliente"], row["plato_favorito"], restaurante)
    ok = await _send_whatsapp(settings, tenant_id, row["telefono"], message)
    if ok:
        logger.info(
            "Loyalty outreach sent to %s (%s, %d days overdue)",
            row["nombre"], row["estado_cliente"], days_since - row["frecuencia_dias"],
        )
        return "sent"
    return "skip"


async def trigger_loyalty_outreach(
    settings: ApiExecuteSettings,
    db: AsyncSession,
    tenant_id: UUID,
    *,
    max_messages: int = 10,
) -> dict:
    """Send WhatsApp outreach to at-risk VIP/FRECUENTE customers.

    Targets customers whose days_since_visit > frecuencia_dias * 1.5.
    """
    restaurante = await _fetch_restaurant_name(db, tenant_id)
    rows = await _fetch_at_risk_customers(db, tenant_id, max_messages * 2)
    now = datetime.now(timezone.utc)
    sent, skipped = 0, 0

    for row in rows:
        if sent >= max_messages:
            break
        outcome = await _send_outreach_to_row(settings, tenant_id, row, restaurante, now)
        sent += 1 if outcome == "sent" else 0
        skipped += 1 if outcome == "not_overdue" else 0

    logger.info("Loyalty outreach: %d sent, %d skipped (not overdue)", sent, skipped)
    return {"sent": sent, "skipped": skipped, "total_candidates": len(rows)}


async def _send_whatsapp(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    telefono: str,
    message: str,
) -> bool:
    """Send a WhatsApp message via canales_service."""
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
        logger.warning("Failed to send loyalty WhatsApp to %s", telefono, exc_info=True)
        return False
