"""Mesa routes: CRUD for restaurant tables and availability."""

from datetime import date, time
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import (
    AdminWriter,
    AnyAuthenticated,
    MesaReader,
    MesaWriter,
    get_user_sucursal_id,
)
from app.schemas.mesa import (
    MesaCreate,
    MesaDisponibilidadItem,
    MesaDisponibilidadLegacyItem,
    MesaDisponibilidadResponse,
    MesaResponse,
    MesaUpdate,
)
from app.services import mesa_svc

router = APIRouter(prefix="/mesas", tags=["mesas"])
availability_router = APIRouter(prefix="/mesas", tags=["mesas"])


def _build_availability_response(
    disponibles: list[dict],
    fecha: date,
    hora: time,
    personas: int,
) -> MesaDisponibilidadResponse:
    items = [MesaDisponibilidadItem(**mesa) for mesa in disponibles]
    legacy_items = [MesaDisponibilidadLegacyItem(**mesa) for mesa in disponibles]
    return MesaDisponibilidadResponse(
        disponibles=items,
        mesas=legacy_items,
        fecha=fecha,
        hora=hora,
        personas=personas,
    )


@router.get("/disponibilidad", response_model=MesaDisponibilidadResponse)
@availability_router.get("/disponibilidad", response_model=MesaDisponibilidadResponse)
async def disponibilidad_mesas(
    fecha: date = Query(...),
    hora: time = Query(...),
    personas: int = Query(..., ge=1, le=50),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List mesas available for a 90-minute reservation slot."""
    disponibles = await mesa_svc.list_available_mesas(
        db, current_user["tenant_id"], fecha, hora, personas,
    )
    return _build_availability_response(disponibles, fecha, hora, personas)


@router.get("", response_model=PaginatedResponse[MesaResponse])
async def list_mesas(
    pagination: PaginationParams = Depends(),
    sucursal_id: UUID | None = Query(None, description="Filter by sucursal"),
    current_user: dict = MesaReader,
    db: AsyncSession = Depends(get_db),
):
    """List mesas for the current tenant. Uses explicit sucursal_id if provided, else user's assigned."""
    effective_sucursal = sucursal_id if sucursal_id else get_user_sucursal_id(current_user)
    return await mesa_svc.list_mesas(
        db, current_user["tenant_id"], pagination,
        sucursal_id=effective_sucursal,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MesaResponse)
async def create_mesa(
    body: MesaCreate,
    current_user: dict = MesaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new mesa (ADMIN, SUPERADMIN, Sudamérica AI)."""
    return await mesa_svc.create_mesa(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.get("/{mesa_id}", response_model=MesaResponse)
async def get_mesa(
    mesa_id: UUID,
    current_user: dict = MesaReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single mesa."""
    return await mesa_svc.get_mesa(db, current_user["tenant_id"], mesa_id)


@router.patch("/{mesa_id}", response_model=MesaResponse)
async def update_mesa(
    mesa_id: UUID,
    body: MesaUpdate,
    current_user: dict = MesaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a mesa (ADMIN, SUPERADMIN, Sudamérica AI)."""
    data = body.model_dump(exclude_unset=True)
    return await mesa_svc.update_mesa(
        db, current_user["tenant_id"], mesa_id, data
    )


@router.delete("/{mesa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesa(
    mesa_id: UUID,
    current_user: dict = MesaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a mesa (ADMIN, SUPERADMIN, Sudamérica AI)."""
    await mesa_svc.soft_delete_mesa(db, current_user["tenant_id"], mesa_id)


@router.post("/{mesa_id}/regenerate-qr", response_model=MesaResponse)
async def regenerate_qr(
    mesa_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new QR token for a mesa, invalidating the old one."""
    return await mesa_svc.regenerate_qr_token(
        db, current_user["tenant_id"], mesa_id
    )
