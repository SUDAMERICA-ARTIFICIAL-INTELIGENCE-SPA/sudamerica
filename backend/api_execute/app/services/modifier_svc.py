"""Modifier service: CRUD for modifier_groups + modifiers + product assignment."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modifier import Modifier, ModifierGroup, ProductoModifierGroup
from app.models.producto import Producto
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud
from shared.utils.exceptions import NotFoundError
from shared.utils.sql_helpers import escape_like


# ─── Modifier Groups ───


async def list_modifier_groups(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    nombre: str | None = None,
) -> PaginatedResponse:
    """List active modifier groups with their modifiers."""
    filters = []
    if nombre:
        filters.append(ModifierGroup.nombre.ilike(f"%{escape_like(nombre)}%"))
    return await crud.list_active(db, ModifierGroup, tenant_id, pagination, extra_filters=filters)


async def get_modifier_group(
    db: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
) -> ModifierGroup:
    """Get a single active modifier group."""
    return await crud.get_by_id(db, ModifierGroup, tenant_id, group_id, label="ModifierGroup")


async def create_modifier_group(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> ModifierGroup:
    """Create a modifier group, optionally with inline modifiers."""
    inline_modifiers = data.pop("modifiers", None) or []
    group = ModifierGroup(tenant_id=tenant_id, **data)
    db.add(group)
    await db.flush()

    for idx, mod_data in enumerate(inline_modifiers):
        modifier = Modifier(
            tenant_id=tenant_id,
            grupo_id=group.id,
            orden=mod_data.get("orden", idx),
            nombre=mod_data["nombre"],
            precio_delta=mod_data.get("precio_delta", 0),
        )
        db.add(modifier)

    await db.flush()
    await db.refresh(group)
    return group


async def update_modifier_group(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    data: dict,
) -> ModifierGroup:
    """Update modifier group fields."""
    return await crud.update_fields(db, ModifierGroup, tenant_id, group_id, data, label="ModifierGroup")


async def soft_delete_modifier_group(
    db: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
) -> ModifierGroup:
    """Soft-delete a modifier group."""
    return await crud.soft_delete(db, ModifierGroup, tenant_id, group_id, label="ModifierGroup")


# ─── Modifiers (options within a group) ───


async def list_modifiers(
    db: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
) -> list[Modifier]:
    """List active modifiers in a group, ordered by `orden`."""
    await get_modifier_group(db, tenant_id, group_id)
    result = await db.execute(
        select(Modifier)
        .where(
            Modifier.grupo_id == group_id,
            Modifier.tenant_id == tenant_id,
            Modifier.activo.is_(True),
        )
        .order_by(Modifier.orden)
    )
    return list(result.scalars().all())


async def create_modifier(
    db: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID, data: dict
) -> Modifier:
    """Create a modifier within a group."""
    await get_modifier_group(db, tenant_id, group_id)
    modifier = Modifier(tenant_id=tenant_id, grupo_id=group_id, **data)
    db.add(modifier)
    await db.flush()
    return modifier


async def update_modifier(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    modifier_id: uuid.UUID,
    data: dict,
) -> Modifier:
    """Update a modifier."""
    return await crud.update_fields(db, Modifier, tenant_id, modifier_id, data, label="Modifier")


async def soft_delete_modifier(
    db: AsyncSession, tenant_id: uuid.UUID, modifier_id: uuid.UUID
) -> None:
    """Soft-delete a modifier."""
    await crud.soft_delete(db, Modifier, tenant_id, modifier_id, label="Modifier")


# ─── Product ↔ Modifier Group Assignment ───


async def assign_modifier_groups_to_product(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    producto_id: uuid.UUID,
    modifier_group_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Replace all modifier group assignments for a product."""
    result = await db.execute(
        select(Producto).where(
            Producto.id == producto_id,
            Producto.tenant_id == tenant_id,
            Producto.activo.is_(True),
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Producto", str(producto_id))

    for gid in modifier_group_ids:
        await get_modifier_group(db, tenant_id, gid)

    await db.execute(
        delete(ProductoModifierGroup).where(
            ProductoModifierGroup.producto_id == producto_id
        )
    )

    for gid in modifier_group_ids:
        db.add(ProductoModifierGroup(producto_id=producto_id, modifier_group_id=gid))

    await db.flush()
    return modifier_group_ids


async def get_product_modifier_groups(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    producto_id: uuid.UUID,
) -> list[ModifierGroup]:
    """Get all modifier groups assigned to a product."""
    result = await db.execute(
        select(ModifierGroup)
        .join(
            ProductoModifierGroup,
            ProductoModifierGroup.modifier_group_id == ModifierGroup.id,
        )
        .where(
            ProductoModifierGroup.producto_id == producto_id,
            ModifierGroup.tenant_id == tenant_id,
            ModifierGroup.activo.is_(True),
        )
    )
    return list(result.scalars().all())
