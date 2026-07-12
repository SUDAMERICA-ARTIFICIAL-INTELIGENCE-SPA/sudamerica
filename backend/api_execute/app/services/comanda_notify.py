"""Notify customers via WhatsApp when their comanda status changes.

Sends a short, templated message per FSM transition (EN_COCINA, LISTO,
EN_RUTA, ENTREGADO). On ENTREGADO it also sends a 1–5 rating prompt as a
second message, so the feedback loop closes without requiring the customer
to start a new thread.

All sends are fire-and-forget: any failure is logged and swallowed so a
broken notification never blocks the FSM transition.
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.config import ApiExecuteSettings
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)


# ── Templates ────────────────────────────────────────────────────────
# Keyed by (ComandaEstado, tipo_entrega). A None tipo_entrega means the
# template applies to every delivery type. Format args: {nombre}, {num},
# {prep_time}.

_STATUS_TEMPLATES: dict[tuple[str, str | None], str] = {
    ("EN_COCINA", None): (
        "🔥 ¡Hola {nombre}! Tu pedido #{num} entró a cocina.\n"
        "Tiempo estimado de preparación: ~{prep_time} min.\n\n"
        "Te avisamos apenas esté listo. 🙌"
    ),
    # EN_PROCESO: fase de preparación genérica de la FSM sin cocina (operativa.py). Sin
    # esta clave la notificación se perdía en silencio para rubros no gastronómicos.
    # Texto neutral (sin "cocina"/🍽️) — restaurante usa EN_COCINA, nunca llega aquí.
    ("EN_PROCESO", None): (
        "⏳ ¡Hola {nombre}! Estamos preparando tu pedido #{num}.\n"
        "Tiempo estimado: ~{prep_time} min.\n\n"
        "Te avisamos apenas esté listo. 🙌"
    ),
    ("LISTO", "RETIRO"): (
        "✅ ¡Hola {nombre}! Tu pedido #{num} ya está listo para retiro.\n"
        "Te esperamos cuando quieras pasarlo a buscar. 😊"
    ),
    ("LISTO", "DELIVERY"): (
        "✅ ¡Hola {nombre}! Tu pedido #{num} ya está listo.\n"
        "El repartidor lo toma en breve para llevártelo. 🛵"
    ),
    ("LISTO", "MESA"): (
        "✅ Tu pedido #{num} ya va a tu mesa. ¡Buen provecho! 🍽️"
    ),
    ("EN_RUTA", None): (
        "🚚 ¡Hola {nombre}! Tu pedido #{num} va en camino.\n"
        "El repartidor ya salió con tu orden. 📦"
    ),
    ("ENTREGADO", None): (
        "🎉 ¡Hola {nombre}! Tu pedido #{num} fue entregado.\n"
        "Gracias por elegirnos. ¡Esperamos que lo disfrutes! 😊"
    ),
}

_RATING_PROMPT = (
    "Cuéntanos cómo fue tu experiencia respondiendo con una nota del 1 al 5 ⭐\n"
    "(1 = mala · 5 = excelente)\n\n"
    "Tu feedback nos ayuda a mejorar. 🙏"
)


# ── Template lookup ──────────────────────────────────────────────────


def _pick_template(estado: str, tipo_entrega: str) -> str | None:
    """Return the most specific template for the (estado, tipo_entrega) pair."""
    key_specific = (estado, tipo_entrega)
    key_generic = (estado, None)
    return _STATUS_TEMPLATES.get(key_specific) or _STATUS_TEMPLATES.get(key_generic)


def build_status_message(
    estado: str,
    tipo_entrega: str,
    comanda_id: UUID,
    nombre: str | None,
    prep_time_min: int = 30,
) -> str | None:
    """Format the status update message for a given transition."""
    template = _pick_template(estado, tipo_entrega)
    if template is None:
        return None
    return template.format(
        nombre=nombre or "cliente",
        num=str(comanda_id)[:8],
        prep_time=prep_time_min,
    )


# ── HTTP sender ──────────────────────────────────────────────────────


async def _send_text(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    telefono: str,
    message: str,
) -> None:
    """Send a single text via canales_service using an internal service JWT."""
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

    resp = await internal_http.post(
        f"{settings.SERVICE_CANALES_URL}/api/v1/canales/whatsapp/send",
        json={"to": telefono, "message": message, "tenant_id": str(tenant_id)},
        headers=headers,
        timeout=15.0,
    )
    resp.raise_for_status()


# ── Public API ───────────────────────────────────────────────────────


async def notify_customer_state_change(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    comanda_id: UUID,
    telefono: str,
    nombre: str | None,
    tipo_entrega: str,
    new_estado: str,
    prep_time_min: int = 30,
) -> None:
    """Send a customer-facing WhatsApp update when a comanda changes state.

    Fire-and-forget. On ENTREGADO, sends a second message asking for a
    1–5 rating. All errors are logged; none propagate.
    """
    message = build_status_message(
        new_estado, tipo_entrega, comanda_id, nombre, prep_time_min
    )
    if not message:
        return

    try:
        await _send_text(settings, tenant_id, telefono, message)
        logger.info(
            "Status notification sent to %s (tenant %s, comanda %s → %s)",
            telefono,
            tenant_id,
            comanda_id,
            new_estado,
        )
    except (httpx.HTTPError, RuntimeError):
        logger.warning(
            "Failed to send status notification to %s (comanda %s → %s)",
            telefono,
            comanda_id,
            new_estado,
            exc_info=True,
        )
        return

    if new_estado == "ENTREGADO":
        try:
            await _send_text(settings, tenant_id, telefono, _RATING_PROMPT)
            logger.info(
                "Rating prompt sent to %s (comanda %s)", telefono, comanda_id
            )
        except (httpx.HTTPError, RuntimeError):
            logger.warning(
                "Failed to send rating prompt to %s (comanda %s)",
                telefono,
                comanda_id,
                exc_info=True,
            )


# ── Backwards-compatible alias (deprecated) ──────────────────────────
# The old `notify_order_ready` only handled LISTO. Kept as a thin wrapper
# so existing callers and tests keep working during the transition.

_LEGACY_LISTO_TEMPLATES = {
    "RETIRO": _STATUS_TEMPLATES[("LISTO", "RETIRO")],
    "DELIVERY": _STATUS_TEMPLATES[("LISTO", "DELIVERY")],
}


async def notify_order_ready(
    settings: ApiExecuteSettings,
    tenant_id: UUID,
    telefono: str,
    cliente_nombre: str | None,
    tipo_entrega: str,
) -> None:
    """Deprecated: use ``notify_customer_state_change`` with new_estado='LISTO'."""
    template = _LEGACY_LISTO_TEMPLATES.get(tipo_entrega)
    if not template:
        return
    nombre = cliente_nombre or "cliente"
    # The legacy template doesn't include {num}/{prep_time}, so feed placeholders.
    message = template.format(nombre=nombre, num="", prep_time=30)
    try:
        await _send_text(settings, tenant_id, telefono, message)
        logger.info(
            "Order-ready notification sent to %s (tenant %s)", telefono, tenant_id
        )
    except (httpx.HTTPError, RuntimeError):
        logger.warning(
            "Failed to send order-ready notification to %s", telefono, exc_info=True
        )
