"""Public QR endpoint — scanned by customers at their table.

No JWT required. Validates the QR token and redirects to WhatsApp.
"""

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import (
    get_db,
    set_instance_lookup_context,
    set_qr_lookup_context,
)

from app.services.mesa_svc import get_mesa_by_qr_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mesas", tags=["mesa-qr"])

_ERROR_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Mesa no disponible</title>
<style>body{{font-family:system-ui;display:flex;align-items:center;justify-content:center;
min-height:100vh;margin:0;background:#f9fafb}}
.card{{text-align:center;padding:2rem;border-radius:12px;box-shadow:0 1px 6px rgba(0,0,0,.1);
background:#fff;max-width:400px}}.card h1{{font-size:1.5rem;margin:0 0 .5rem}}
.card p{{color:#666;margin:0}}</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p></div></body></html>"""


def _instance_name_for_tenant(tenant_id: str) -> str:
    return f"tenant-{tenant_id}"


async def _get_whatsapp_phone(db: AsyncSession, instance_name: str) -> str | None:
    """Find the public WhatsApp phone for the current tenant instance."""
    result = await db.execute(
        sql_text(
            "SELECT instance_name, phone_number, status "
            "FROM evolution_instances "
            "WHERE instance_name = :instance_name "
            "AND activo = true "
            "AND phone_number IS NOT NULL "
            "LIMIT 1"
        ),
        {"instance_name": instance_name},
    )
    row = result.mappings().first()
    return row["phone_number"] if row else None


@router.get("/qr/{qr_token}")
async def scan_mesa_qr(
    qr_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: client scans QR at their table -> redirect to WhatsApp."""
    await set_qr_lookup_context(db)
    mesa = await get_mesa_by_qr_token(db, qr_token)

    if not mesa:
        return HTMLResponse(
            _ERROR_HTML.format(
                title="QR no valido",
                message="Este codigo QR no corresponde a ninguna mesa activa.",
            ),
            status_code=404,
        )

    if not mesa["activo"]:
        return HTMLResponse(
            _ERROR_HTML.format(
                title="Mesa no disponible",
                message="Esta mesa no esta habilitada en este momento.",
            ),
            status_code=404,
        )

    instance_name = _instance_name_for_tenant(str(mesa["tenant_id"]))
    await set_instance_lookup_context(db, instance_name)
    phone = await _get_whatsapp_phone(db, instance_name)
    if not phone:
        return HTMLResponse(
            _ERROR_HTML.format(
                title="WhatsApp no configurado",
                message="El restaurante aun no tiene WhatsApp conectado. "
                "Consulta directamente con el personal.",
            ),
            status_code=503,
        )

    sucursal_name = mesa.get("sucursal_nombre") or ""
    location = f" de {sucursal_name}" if sucursal_name else ""
    greeting = (
        f"Hola! Estoy en mesa {mesa['numero']}{location}. "
        f"Quiero ver el menu. [mesa:{qr_token}]"
    )

    # Strip leading + and non-digits for wa.me format
    clean_phone = "".join(c for c in phone if c.isdigit())
    whatsapp_url = f"https://wa.me/{clean_phone}?text={quote(greeting)}"

    logger.info(
        "QR scan: mesa=%s, tenant=%s -> redirecting to WhatsApp",
        mesa["numero"], mesa["tenant_id"],
    )
    return RedirectResponse(url=whatsapp_url, status_code=302)
