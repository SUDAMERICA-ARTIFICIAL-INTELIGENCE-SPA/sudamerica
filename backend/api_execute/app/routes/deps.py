"""Shared route dependencies — centralizes auth guards and common helpers.

Import these instead of repeating Depends(require_role(...)) in every route file.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Request

from shared.middleware.auth import get_current_user, require_role, require_user_or_service
from shared.models.enums import UserRole
from shared.utils.service_access import (
    CARTA_READERS,
    CARTA_WRITERS,
    COMANDA_READERS,
    COMANDA_WRITERS,
    LEAD_READERS,
    LEAD_WRITERS,
    MESA_READERS,
    MESA_WRITERS,
    METRICAS_READERS,
    MODIFIER_READERS,
    MODIFIER_WRITERS,
    ORCHESTRATOR_CHAT_CALLERS,
    USUARIO_READERS,
    USUARIO_WRITERS,
    VENTA_READERS,
    VENTA_WRITERS,
)

from app.config import ApiExecuteSettings

# ─── Settings helper ───


def get_settings(request: Request) -> ApiExecuteSettings:
    """Extract settings from app state."""
    return request.app.state.settings


# ─── Role-based guards (reusable across routes) ───

AdminWriter = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN))
"""SUPERADMIN or ADMIN — used for create/update/delete operations."""

SuperAdminOnly = Depends(require_role(UserRole.SUPERADMIN))
"""SUPERADMIN only — used for platform-level admin operations."""

AnyAuthenticated = Depends(get_current_user)
"""Any authenticated user regardless of role."""


# ─── All roles shorthand ───

_ALL_ROLES = (
    UserRole.SUPERADMIN,
    UserRole.ADMIN,
    UserRole.GERENTE,
    UserRole.MESERO,
    UserRole.COCINA,
    UserRole.CAJA,
    UserRole.PERSONAL,
    UserRole.ASESOR,
    UserRole.VIEWER,
)

_WRITE_ROLES = (
    UserRole.SUPERADMIN,
    UserRole.ADMIN,
    UserRole.GERENTE,
    UserRole.MESERO,
    UserRole.COCINA,
    UserRole.CAJA,
    UserRole.PERSONAL,
    UserRole.ASESOR,
)


# ─── Carta (menu) guards ───

CartaReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("categorias:read", "productos:read"),
        service_callers=CARTA_READERS,
    )
)
"""Read access to menu items (categorias, productos) — all user roles + services."""

CartaWriter = Depends(
    require_user_or_service(
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        service_scopes=("categorias:write", "productos:write"),
        service_callers=CARTA_WRITERS,
    )
)
"""Write access to menu items — SUPERADMIN/ADMIN + open_agent."""


# ─── Leads guards ───

LeadReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("leads:read",),
        service_callers=LEAD_READERS,
    )
)
"""Read access to leads — all user roles + services."""

LeadWriter = Depends(
    require_user_or_service(
        *_WRITE_ROLES,
        service_scopes=("leads:write",),
        service_callers=LEAD_WRITERS,
    )
)
"""Write access to leads — SUPERADMIN/ADMIN/PERSONAL/ASESOR + services."""


# ─── Ventas guards ───

VentaReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("ventas:read",),
        service_callers=VENTA_READERS,
    )
)
"""Read access to ventas — all user roles + open_agent."""

VentaWriter = Depends(
    require_user_or_service(
        *_WRITE_ROLES,
        service_scopes=("ventas:write",),
        service_callers=VENTA_WRITERS,
    )
)
"""Write access to ventas — SUPERADMIN/ADMIN/PERSONAL/ASESOR + open_agent."""


# ─── Comandas guards ───

ComandaReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("comandas:read",),
        service_callers=COMANDA_READERS,
    )
)
"""Read access to comandas — all user roles + services."""

ComandaWriter = Depends(
    require_user_or_service(
        *_WRITE_ROLES,
        service_scopes=("comandas:write",),
        service_callers=COMANDA_WRITERS,
    )
)
"""Write access to comandas — SUPERADMIN/ADMIN/PERSONAL/ASESOR + services."""


# ─── Modifiers guards ───

ModifierReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("modifiers:read",),
        service_callers=MODIFIER_READERS,
    )
)
"""Read access to modifiers — all user roles + services."""

ModifierWriter = Depends(
    require_user_or_service(
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        service_scopes=("modifiers:write",),
        service_callers=MODIFIER_WRITERS,
    )
)
"""Write access to modifiers — SUPERADMIN/ADMIN + open_agent."""


# ─── Mesas guards ───

MesaReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("mesas:read",),
        service_callers=MESA_READERS,
    )
)
"""Read access to mesas — all user roles + open_agent."""

MesaWriter = Depends(
    require_user_or_service(
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        service_scopes=("mesas:write",),
        service_callers=MESA_WRITERS,
    )
)
"""Write access to mesas — SUPERADMIN/ADMIN + open_agent."""


# ─── Usuarios guards ───

UsuarioReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("usuarios:read",),
        service_callers=USUARIO_READERS,
    )
)
"""Read access to usuarios — all user roles + open_agent."""

UsuarioWriter = Depends(
    require_user_or_service(
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        service_scopes=("usuarios:write",),
        service_callers=USUARIO_WRITERS,
    )
)
"""Write access to usuarios — SUPERADMIN/ADMIN + open_agent."""


# ─── Metricas guards ───

MetricasReader = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("metricas:read",),
        service_callers=METRICAS_READERS,
    )
)
"""Read access to metricas — all user roles + open_agent."""


# ─── AI Orchestrator guards ───

AiChatActor = Depends(
    require_user_or_service(
        *_ALL_ROLES,
        service_scopes=("chat:write",),
        service_callers=ORCHESTRATOR_CHAT_CALLERS,
    )
)
"""Actor for AI chat — all user roles + canales_service."""


# ─── Branch (sucursal) access helper ───


def require_branch_access(current_user: dict, target_sucursal_id: UUID | None) -> None:
    """Raise 403 if a branch-scoped user tries to access a different branch.

    Rules:
    - SUPERADMIN → always allowed (platform-level)
    - user.sucursal_id is None → admin global del restaurant (all branches)
    - user.sucursal_id matches target → allowed
    - otherwise → 403
    """
    if current_user.get("type") == "service":
        return
    if current_user["role"] == UserRole.SUPERADMIN:
        return
    user_suc = current_user.get("sucursal_id")
    if user_suc is None:
        return  # admin global del restaurant
    if target_sucursal_id is not None and user_suc != target_sucursal_id:
        raise HTTPException(403, "No autorizado para esta sucursal")


def get_user_sucursal_id(current_user: dict) -> UUID | None:
    """Extract sucursal_id from user context for auto-filtering queries."""
    return current_user.get("sucursal_id")
