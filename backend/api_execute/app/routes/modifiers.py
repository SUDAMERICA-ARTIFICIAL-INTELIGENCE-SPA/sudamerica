"""Modifier routes: CRUD for modifier groups, modifiers, and product assignment."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import AdminWriter, ModifierReader, ModifierWriter
from app.schemas.modifier import (
    ModifierCreate,
    ModifierGroupCreate,
    ModifierGroupResponse,
    ModifierGroupUpdate,
    ModifierResponse,
    ModifierUpdate,
    ProductoModifierGroupAssign,
)
from app.services import modifier_svc

router = APIRouter(prefix="/modifier-groups", tags=["modifiers"])


# ─── Modifier Groups ───


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ModifierGroupResponse)
async def create_modifier_group(
    body: ModifierGroupCreate,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new modifier group (optionally with inline modifiers)."""
    return await modifier_svc.create_modifier_group(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.get("", response_model=PaginatedResponse[ModifierGroupResponse])
async def list_modifier_groups(
    pagination: PaginationParams = Depends(),
    nombre: str | None = Query(None),
    current_user: dict = ModifierReader,
    db: AsyncSession = Depends(get_db),
):
    """List modifier groups."""
    return await modifier_svc.list_modifier_groups(
        db, current_user["tenant_id"], pagination, nombre=nombre
    )


@router.get("/{group_id}", response_model=ModifierGroupResponse)
async def get_modifier_group(
    group_id: UUID,
    current_user: dict = ModifierReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single modifier group with its modifiers."""
    return await modifier_svc.get_modifier_group(
        db, current_user["tenant_id"], group_id
    )


@router.patch("/{group_id}", response_model=ModifierGroupResponse)
async def update_modifier_group(
    group_id: UUID,
    body: ModifierGroupUpdate,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a modifier group."""
    data = body.model_dump(exclude_unset=True)
    return await modifier_svc.update_modifier_group(
        db, current_user["tenant_id"], group_id, data
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modifier_group(
    group_id: UUID,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a modifier group."""
    await modifier_svc.soft_delete_modifier_group(
        db, current_user["tenant_id"], group_id
    )


# ─── Modifiers (options within a group) ───


@router.get("/{group_id}/modifiers", response_model=list[ModifierResponse])
async def list_modifiers(
    group_id: UUID,
    current_user: dict = ModifierReader,
    db: AsyncSession = Depends(get_db),
):
    """List modifiers in a group."""
    return await modifier_svc.list_modifiers(
        db, current_user["tenant_id"], group_id
    )


@router.post(
    "/{group_id}/modifiers",
    status_code=status.HTTP_201_CREATED,
    response_model=ModifierResponse,
)
async def create_modifier(
    group_id: UUID,
    body: ModifierCreate,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a modifier within a group."""
    return await modifier_svc.create_modifier(
        db, current_user["tenant_id"], group_id, body.model_dump()
    )


@router.patch("/modifiers/{modifier_id}", response_model=ModifierResponse)
async def update_modifier(
    modifier_id: UUID,
    body: ModifierUpdate,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a modifier."""
    data = body.model_dump(exclude_unset=True)
    return await modifier_svc.update_modifier(
        db, current_user["tenant_id"], modifier_id, data
    )


@router.delete("/modifiers/{modifier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modifier(
    modifier_id: UUID,
    current_user: dict = ModifierWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a modifier."""
    await modifier_svc.soft_delete_modifier(
        db, current_user["tenant_id"], modifier_id
    )


# ─── Product ↔ Modifier Group Assignment ───


@router.get(
    "/productos/{producto_id}",
    response_model=list[ModifierGroupResponse],
    tags=["productos"],
)
async def get_product_modifier_groups(
    producto_id: UUID,
    current_user: dict = ModifierReader,
    db: AsyncSession = Depends(get_db),
):
    """Get modifier groups assigned to a product."""
    return await modifier_svc.get_product_modifier_groups(
        db, current_user["tenant_id"], producto_id
    )


@router.patch(
    "/productos/{producto_id}",
    response_model=list[str],
    tags=["productos"],
)
async def assign_product_modifier_groups(
    producto_id: UUID,
    body: ProductoModifierGroupAssign,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Assign modifier groups to a product (replaces existing assignments)."""
    ids = await modifier_svc.assign_modifier_groups_to_product(
        db, current_user["tenant_id"], producto_id, body.modifier_group_ids
    )
    return [str(i) for i in ids]
