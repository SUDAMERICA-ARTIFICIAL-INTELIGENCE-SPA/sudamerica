"""Sucursales routes: CRUD for multi-location management."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.utils.http_client import HttpClient

from app.routes.deps import AdminWriter, AnyAuthenticated, get_settings, require_branch_access
from app.schemas.sucursal import SucursalCreate, SucursalResponse, SucursalUpdate
from app.services import sucursal_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sucursales", tags=["sucursales"])


@router.get("", response_model=list[SucursalResponse])
async def list_sucursales(
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List active sucursales for the current tenant."""
    rows = await sucursal_svc.list_sucursales(db, current_user["tenant_id"])
    return rows


@router.get("/{sucursal_id}", response_model=SucursalResponse)
async def get_sucursal(
    sucursal_id: UUID,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get a single sucursal by ID."""
    return await sucursal_svc.get_sucursal(
        db, current_user["tenant_id"], sucursal_id
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SucursalResponse)
async def create_sucursal(
    body: SucursalCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new sucursal (ADMIN only). Enforces plan limits."""
    return await sucursal_svc.create_sucursal(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.patch("/{sucursal_id}", response_model=SucursalResponse)
async def update_sucursal(
    sucursal_id: UUID,
    body: SucursalUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update sucursal fields (ADMIN only). Branch-scoped admins can only edit their own."""
    require_branch_access(current_user, sucursal_id)
    data = body.model_dump(exclude_unset=True)
    return await sucursal_svc.update_sucursal(
        db, current_user["tenant_id"], sucursal_id, data
    )


@router.delete("/{sucursal_id}", response_model=SucursalResponse)
async def deactivate_sucursal(
    sucursal_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a sucursal (ADMIN only). Branch-scoped admins can only delete their own."""
    require_branch_access(current_user, sucursal_id)
    return await sucursal_svc.deactivate_sucursal(
        db, current_user["tenant_id"], sucursal_id
    )


import re as _re

_INVITE_CODE_RE = _re.compile(r"chat\.whatsapp\.com/([A-Za-z0-9]+)")


def _extract_invite_code(link_or_code: str) -> str | None:
    """Extract the invite code from a WhatsApp group link or bare code."""
    if not link_or_code:
        return None
    link_or_code = link_or_code.strip()
    match = _INVITE_CODE_RE.search(link_or_code)
    if match:
        return match.group(1)
    # Bare code (no URL)
    if _re.fullmatch(r"[A-Za-z0-9]{10,30}", link_or_code):
        return link_or_code
    return None


@router.post("/{sucursal_id}/grupo-repartidores", response_model=SucursalResponse)
async def set_grupo_repartidores(
    sucursal_id: UUID,
    body: dict,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
):
    """Set the driver WhatsApp group for a sucursal from an invite link.

    Body: ``{"invite_link": "https://chat.whatsapp.com/XXXX"}`` or
    ``{"invite_code": "XXXX"}``. The server resolves the link to a JID via
    Evolution API and stores it in ``sucursales.grupo_repartidores_jid``.

    The tenant's WhatsApp instance must already be a member of the group.
    """
    from fastapi import HTTPException

    require_branch_access(current_user, sucursal_id)
    tenant_id = current_user["tenant_id"]

    link = body.get("invite_link") or body.get("invite_code") or ""
    invite_code = _extract_invite_code(link)
    if not invite_code:
        raise HTTPException(
            status_code=422,
            detail="Enlace inválido. Usa el formato https://chat.whatsapp.com/XXXXX",
        )

    # Load tenant's Evolution instance
    result = await db.execute(
        sql_text(
            "SELECT instance_name FROM evolution_instances "
            "WHERE tenant_id = :tid AND activo = true LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=400,
            detail="No hay instancia de WhatsApp conectada para este tenant.",
        )
    instance_name = row["instance_name"]

    # Call Evolution API /group/inviteInfo to resolve the invite code → group info
    evo_url = getattr(settings, "EVOLUTION_API_URL", "")
    evo_key = getattr(settings, "EVOLUTION_API_KEY", "")
    if not evo_url or not evo_key:
        raise HTTPException(
            status_code=500,
            detail="Evolution API no está configurado en el servidor.",
        )

    try:
        client = HttpClient(base_url=evo_url, timeout=15.0)
        resp = await client.get(
            f"/group/inviteInfo/{instance_name}?inviteCode={invite_code}",
            headers={"apikey": evo_key},
        )
        resp.raise_for_status()
        info = resp.json()
    except Exception as exc:
        logger.warning("Failed to resolve invite code %s: %s", invite_code, exc)
        raise HTTPException(
            status_code=502,
            detail="No se pudo resolver el enlace del grupo. Verifica que "
            "el número del restaurante esté dentro del grupo.",
        ) from exc

    group_jid = info.get("id", "")
    group_name = info.get("subject", "Sin nombre")
    if not group_jid.endswith("@g.us"):
        raise HTTPException(
            status_code=502,
            detail="La respuesta de Evolution API no contiene un JID válido.",
        )

    # Verify the bot is actually a member of the group
    participants = info.get("participants", [])
    participant_phones = [
        p.get("phoneNumber", "").split("@")[0]
        for p in participants if isinstance(p, dict)
    ]

    logger.info(
        "Resolved group invite %s → %s (%s) with %d members",
        invite_code, group_jid, group_name, len(participant_phones),
    )

    # Update the sucursal
    updated = await sucursal_svc.update_sucursal(
        db, tenant_id, sucursal_id, {"grupo_repartidores_jid": group_jid},
    )
    return updated


@router.get("/whatsapp-groups", response_model=list[dict])
async def list_whatsapp_groups(
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
    settings=Depends(get_settings),
):
    """List WhatsApp groups the tenant's instance belongs to (for driver group config)."""
    tenant_id = current_user["tenant_id"]
    result = await db.execute(
        sql_text(
            "SELECT instance_name, evo_token FROM evolution_instances "
            "WHERE tenant_id = :tid AND activo = true LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        return []

    try:
        evo_url = getattr(settings, "EVOLUTION_API_URL", "")
        if not evo_url:
            evo_url = getattr(settings, "SERVICE_CANALES_URL", "http://localhost:8004")
            # Proxy through canales_service or direct Evolution API
        client = HttpClient(base_url=evo_url, timeout=10.0)
        evo_key = getattr(settings, "EVOLUTION_API_KEY", row.get("evo_token", ""))
        resp = await client.get(
            f"/group/fetchAllGroups/{row['instance_name']}",
            headers={"apikey": evo_key},
        )
        resp.raise_for_status()
        groups = resp.json()
        return [
            {"jid": g.get("id", ""), "name": g.get("subject", g.get("name", "Sin nombre"))}
            for g in groups
            if g.get("id", "").endswith("@g.us")
        ]
    except Exception:
        logger.warning("Failed to fetch WhatsApp groups", exc_info=True)
        return []
