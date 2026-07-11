"""Producto service: CRUD + filters + reactivar."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud
from shared.utils.sql_helpers import escape_like

from app.models.producto import Producto


async def list_productos(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    categoria_id: uuid.UUID | None = None,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
    nombre: str | None = None,
    disponible: bool | None = None,
) -> PaginatedResponse:
    """List active productos with optional filters."""
    filters = _build_filters(categoria_id, precio_min, precio_max, nombre, disponible)
    return await crud.list_active(db, Producto, tenant_id, pagination, extra_filters=filters)


def _build_filters(categoria_id, precio_min, precio_max, nombre, disponible):
    """Build SQLAlchemy filter clauses for productos."""
    filters = []
    if categoria_id:
        filters.append(Producto.categoria_id == categoria_id)
    if precio_min is not None:
        filters.append(Producto.precio >= precio_min)
    if precio_max is not None:
        filters.append(Producto.precio <= precio_max)
    if nombre:
        filters.append(Producto.nombre.ilike(f"%{escape_like(nombre)}%"))
    if disponible is not None:
        filters.append(Producto.disponible.is_(disponible))
    return filters


async def get_producto(
    db: AsyncSession, tenant_id: uuid.UUID, producto_id: uuid.UUID
) -> Producto:
    """Get a single active producto."""
    return await crud.get_by_id(db, Producto, tenant_id, producto_id, label="Producto")


async def create_producto(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Producto:
    """Create a new producto."""
    if data.get("categoria_id"):
        await crud.require_exists(db, Categoria, tenant_id, data["categoria_id"], label="Categoria")
    return await crud.create_one(db, Producto, tenant_id, data)


async def update_producto(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    producto_id: uuid.UUID,
    data: dict,
) -> Producto:
    """Update producto fields."""
    if data.get("categoria_id") is not None:
        await crud.require_exists(db, Categoria, tenant_id, data["categoria_id"], label="Categoria")
    return await crud.update_fields(db, Producto, tenant_id, producto_id, data, label="Producto")


async def soft_delete_producto(
    db: AsyncSession, tenant_id: uuid.UUID, producto_id: uuid.UUID
) -> Producto:
    """Soft-delete a producto."""
    return await crud.soft_delete(db, Producto, tenant_id, producto_id, label="Producto")


async def reactivar_producto(
    db: AsyncSession, tenant_id: uuid.UUID, producto_id: uuid.UUID
) -> Producto:
    """Reactivate a soft-deleted producto."""
    return await crud.reactivate(db, Producto, tenant_id, producto_id, label="Producto")


