"""Lead routes: CRUD + FSM transition + filter by estado."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import AnyAuthenticated, LeadReader, LeadWriter
from app.schemas.lead import LeadCreate, LeadResponse, LeadTransicion, LeadUpdate
from app.services import lead_svc

router = APIRouter(prefix="/leads", tags=["leads"])

_ALLOWED_ORDER_BY = {"total_gastado", "total_pedidos", "ultima_visita", "frecuencia_dias"}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LeadResponse)
async def create_lead(
    body: LeadCreate,
    current_user: dict = LeadWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead (defaults to NUEVO)."""
    return await lead_svc.create_lead(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.get("", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    pagination: PaginationParams = Depends(),
    estado: str | None = Query(None),
    canal: str | None = Query(None),
    asignado_a: UUID | None = Query(None),
    telefono: str | None = Query(None),
    estado_cliente: str | None = Query(None),
    order_by: str | None = Query(None),
    current_user: dict = LeadReader,
    db: AsyncSession = Depends(get_db),
):
    """List leads with optional filters."""
    if order_by and order_by not in _ALLOWED_ORDER_BY:
        raise HTTPException(
            status_code=422,
            detail=f"order_by must be one of: {sorted(_ALLOWED_ORDER_BY)}",
        )
    return await lead_svc.list_leads(
        db, current_user["tenant_id"], pagination,
        estado=estado, canal=canal, asignado_a=asignado_a, telefono=telefono,
        estado_cliente=estado_cliente, order_by=order_by,
    )


@router.get("/estado/{estado}", response_model=PaginatedResponse[LeadResponse])
async def list_leads_by_estado(
    estado: str,
    pagination: PaginationParams = Depends(),
    current_user: dict = LeadReader,
    db: AsyncSession = Depends(get_db),
):
    """List leads filtered by estado."""
    return await lead_svc.list_leads_by_estado(
        db, current_user["tenant_id"], estado, pagination
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    current_user: dict = LeadReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single lead."""
    return await lead_svc.get_lead(db, current_user["tenant_id"], lead_id)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    body: LeadUpdate,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Update lead fields (NOT estado)."""
    data = body.model_dump(exclude_unset=True)
    return await lead_svc.update_lead(
        db, current_user["tenant_id"], lead_id, data
    )


@router.patch("/{lead_id}/estado", response_model=LeadResponse)
async def transition_lead_estado(
    lead_id: UUID,
    body: LeadTransicion,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """FSM transition: validates allowed transitions, returns 422 on invalid."""
    return await lead_svc.transition_estado(
        db, current_user["tenant_id"], lead_id, body.estado
    )
