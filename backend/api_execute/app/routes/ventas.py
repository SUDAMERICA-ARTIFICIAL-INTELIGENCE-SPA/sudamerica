"""Venta routes: POST, GET list, GET/{id}."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import VentaReader, get_user_sucursal_id
from app.schemas.venta import VentaCreate, VentaResponse
from app.services import venta_svc

router = APIRouter(prefix="/ventas", tags=["ventas"])


def _parse_datetime_query(value: str | None, field_name: str) -> datetime | None:
    """Accept standard ISO8601 query params and tolerate `+00:00` decoded as space."""
    if value is None:
        return None

    candidates = [value.strip()]
    if candidates[0].endswith("Z"):
        candidates.append(f"{candidates[0][:-1]}+00:00")

    if " " in candidates[0] and "T" in candidates[0]:
        head, tail = candidates[0].rsplit(" ", 1)
        if ":" in tail:
            candidates.append(f"{head}+{tail}")

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid datetime for '{field_name}'",
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VentaResponse)
async def create_venta(
    body: VentaCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a venta (total computed server-side, immutable)."""
    return await venta_svc.create_venta(
        db,
        current_user["tenant_id"],
        current_user["user_id"],
        body.model_dump(),
    )


@router.get("", response_model=PaginatedResponse[VentaResponse])
async def list_ventas(
    pagination: PaginationParams = Depends(),
    asesor_id: UUID | None = Query(None),
    lead_id: UUID | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    current_user: dict = VentaReader,
    db: AsyncSession = Depends(get_db),
):
    """List ventas for the current tenant, auto-filtered by user's sucursal."""
    return await venta_svc.list_ventas(
        db,
        current_user["tenant_id"],
        pagination,
        asesor_id=asesor_id,
        lead_id=lead_id,
        fecha_desde=_parse_datetime_query(fecha_desde, "fecha_desde"),
        fecha_hasta=_parse_datetime_query(fecha_hasta, "fecha_hasta"),
        sucursal_id=get_user_sucursal_id(current_user),
    )


@router.get("/{venta_id}", response_model=VentaResponse)
async def get_venta(
    venta_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single venta."""
    return await venta_svc.get_venta(
        db, current_user["tenant_id"], venta_id
    )
