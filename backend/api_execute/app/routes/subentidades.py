"""Sub-entidades del cliente (mascota/vehículo/propiedad/paciente) — F6 multi-rubro.

Rutas gateadas por el módulo SUB_ENTIDAD del rubro del tenant (403 si no aplica).
"""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.rubros import rubro_def
from shared.utils.exceptions import ForbiddenError

from app.routes.deps import AdminWriter, AnyAuthenticated
from app.schemas.subentidad import (
    SubentidadCreate,
    SubentidadResponse,
    SubentidadUpdate,
)
from app.services import subentidad_svc
from app.services.tenant_rubro import load_tenant_rubro

router = APIRouter(prefix="/subentidades", tags=["subentidades"])


async def _ensure_modulo(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """403 si el rubro del tenant no tiene ficha de sub-entidad (label presente ⟺ habilitado)."""
    rubro = await load_tenant_rubro(db, tenant_id)
    if rubro_def(rubro).sub_entidad_label is None:
        raise ForbiddenError("El módulo de sub-entidades no está habilitado para este rubro")


@router.get("", response_model=list[SubentidadResponse])
async def list_subentidades(
    lead_id: UUID | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Lista sub-entidades activas del tenant (opcionalmente por cliente)."""
    await _ensure_modulo(db, current_user["tenant_id"])
    rows = await subentidad_svc.list_subentidades(
        db, current_user["tenant_id"], lead_id=lead_id
    )
    return [SubentidadResponse.model_validate(r) for r in rows]


@router.post("", response_model=SubentidadResponse, status_code=status.HTTP_201_CREATED)
async def create_subentidad(
    body: SubentidadCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Crea una sub-entidad asociada a un cliente."""
    await _ensure_modulo(db, current_user["tenant_id"])
    row = await subentidad_svc.create_subentidad(
        db, current_user["tenant_id"], body.model_dump()
    )
    await db.commit()
    return SubentidadResponse.model_validate(row)


@router.patch("/{subentidad_id}", response_model=SubentidadResponse)
async def update_subentidad(
    subentidad_id: UUID,
    body: SubentidadUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una sub-entidad (tipo, nombre, datos)."""
    await _ensure_modulo(db, current_user["tenant_id"])
    row = await subentidad_svc.update_subentidad(
        db, current_user["tenant_id"], subentidad_id,
        body.model_dump(exclude_unset=True),
    )
    await db.commit()
    return SubentidadResponse.model_validate(row)


@router.delete("/{subentidad_id}", response_model=SubentidadResponse)
async def delete_subentidad(
    subentidad_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete de una sub-entidad."""
    await _ensure_modulo(db, current_user["tenant_id"])
    row = await subentidad_svc.delete_subentidad(
        db, current_user["tenant_id"], subentidad_id
    )
    await db.commit()
    return SubentidadResponse.model_validate(row)
