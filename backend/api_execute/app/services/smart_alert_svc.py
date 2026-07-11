"""SmartAlert service: list, get, update (mark read)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud

from app.models.smart_alert import SmartAlert


async def list_alerts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    tipo: str | None = None,
    leido: bool | None = None,
) -> dict:
    """List alerts for a tenant with optional filters.

    Returns a legacy-format dict (the route has no response_model).
    """
    filters = []
    if tipo:
        filters.append(SmartAlert.tipo == tipo)
    if leido is not None:
        filters.append(SmartAlert.leido.is_(leido))
    result = await crud.list_active(db, SmartAlert, tenant_id, pagination, extra_filters=filters)
    return {
        "success": True,
        "data": result.data,
        "error": None,
        "meta": result.meta,
    }


async def get_alert(
    db: AsyncSession, tenant_id: uuid.UUID, alert_id: uuid.UUID
) -> SmartAlert:
    """Get a single alert by ID."""
    return await crud.get_by_id(db, SmartAlert, tenant_id, alert_id, label="SmartAlert")


async def update_alert(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    data: dict,
) -> SmartAlert:
    """Update alert fields (e.g. mark as read)."""
    return await crud.update_fields(db, SmartAlert, tenant_id, alert_id, data, label="SmartAlert")
