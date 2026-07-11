"""Venta service: create (immutable total), list, get."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.producto import Producto
from app.models.usuario import Usuario
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud

from app.models.venta import Venta


async def create_venta(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    data: dict,
) -> Venta:
    """Create a venta. total = cantidad * precio_unitario (immutable)."""
    if data.get("lead_id"):
        await crud.require_exists(db, Lead, tenant_id, data["lead_id"], label="Lead")
    if data.get("producto_id"):
        await crud.require_exists(db, Producto, tenant_id, data["producto_id"], label="Producto")
    if usuario_id is not None:
        await crud.require_exists(db, Usuario, tenant_id, usuario_id, label="Usuario")

    total = Decimal(str(data["cantidad"])) * Decimal(str(data["precio_unitario"]))
    venta = Venta(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        total=total,
        **data,
    )
    db.add(venta)
    await db.flush()
    return venta


async def list_ventas(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    *,
    asesor_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    sucursal_id: uuid.UUID | None = None,
) -> PaginatedResponse:
    """List ventas for a tenant, optionally filtered by sucursal."""
    filters = []
    if asesor_id:
        filters.append(Venta.usuario_id == asesor_id)
    if lead_id:
        filters.append(Venta.lead_id == lead_id)
    if fecha_desde:
        filters.append(Venta.created_at >= fecha_desde)
    if fecha_hasta:
        filters.append(Venta.created_at <= fecha_hasta)
    if sucursal_id is not None:
        filters.append(Venta.sucursal_id == sucursal_id)

    return await crud.list_active(
        db,
        Venta,
        tenant_id,
        pagination,
        extra_filters=filters,
    )


async def get_venta(
    db: AsyncSession, tenant_id: uuid.UUID, venta_id: uuid.UUID
) -> Venta:
    """Get a single venta by ID."""
    return await crud.get_by_id(db, Venta, tenant_id, venta_id, label="Venta")
