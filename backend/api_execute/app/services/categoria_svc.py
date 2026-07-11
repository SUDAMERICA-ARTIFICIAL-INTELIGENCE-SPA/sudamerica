"""Categoria service: CRUD + soft delete."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud

from app.models.categoria import Categoria


async def list_categorias(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
) -> PaginatedResponse:
    """List active categorias for a tenant."""
    return await crud.list_active(db, Categoria, tenant_id, pagination)


async def get_categoria(
    db: AsyncSession, tenant_id: uuid.UUID, categoria_id: uuid.UUID
) -> Categoria:
    """Get a single active categoria."""
    return await crud.get_by_id(db, Categoria, tenant_id, categoria_id, label="Categoria")


async def create_categoria(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Categoria:
    """Create a new categoria."""
    return await crud.create_one(db, Categoria, tenant_id, data)


async def update_categoria(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    categoria_id: uuid.UUID,
    data: dict,
) -> Categoria:
    """Update categoria fields."""
    return await crud.update_fields(db, Categoria, tenant_id, categoria_id, data, label="Categoria")


async def soft_delete_categoria(
    db: AsyncSession, tenant_id: uuid.UUID, categoria_id: uuid.UUID
) -> Categoria:
    """Soft-delete a categoria."""
    return await crud.soft_delete(db, Categoria, tenant_id, categoria_id, label="Categoria")
