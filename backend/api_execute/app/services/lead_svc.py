"""Lead service: CRUD + FSM transition_estado."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from shared.models.enums import LeadEstado
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud
from shared.utils.exceptions import ConflictError, InvalidTransitionError

from app.models.lead import Lead
from app.models.tenant import Tenant


async def list_leads(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    estado: str | None = None,
    canal: str | None = None,
    asignado_a: uuid.UUID | None = None,
    telefono: str | None = None,
    estado_cliente: str | None = None,
    order_by: str | None = None,
) -> PaginatedResponse:
    """List active leads with optional filters."""
    filters = _build_lead_filters(estado, canal, asignado_a, telefono, estado_cliente)
    sort = _resolve_order(order_by)
    return await crud.list_active(
        db, Lead, tenant_id, pagination, extra_filters=filters, order_by=sort,
    )


def _build_lead_filters(estado, canal, asignado_a, telefono, estado_cliente):
    """Build filter clauses for lead queries."""
    filters = []
    if estado:
        filters.append(Lead.estado == estado)
    if canal:
        filters.append(Lead.canal == canal)
    if asignado_a:
        filters.append(Lead.asignado_a == asignado_a)
    if telefono:
        filters.append(Lead.telefono == telefono)
    if estado_cliente:
        filters.append(Lead.estado_cliente == estado_cliente)
    return filters


def _resolve_order(order_by: str | None):
    """Resolve order_by string to SQLAlchemy column expression."""
    if not order_by:
        return None
    col = getattr(Lead, order_by, None)
    return col.desc() if col is not None else None


async def get_lead(
    db: AsyncSession, tenant_id: uuid.UUID, lead_id: uuid.UUID
) -> Lead:
    """Get a single active lead."""
    return await crud.get_by_id(db, Lead, tenant_id, lead_id, label="Lead")


async def create_lead(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Lead:
    """Create a new lead (defaults to NUEVO estado)."""
    tenant_r = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_r.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))

    await _enforce_lead_limit(db, tenant_id, tenant)

    if data.get("asignado_a"):
        await crud.require_exists(db, Usuario, tenant_id, data["asignado_a"], label="Usuario")

    return await crud.create_one(db, Lead, tenant_id, data)


async def _enforce_lead_limit(db, tenant_id, tenant):
    """Raise ConflictError if monthly lead limit is reached."""
    # Lazy plan enforcement: downgrade if a failed-payment grace window expired,
    # so the limit applied below is the one the tenant actually pays for.
    from app.services.mercadopago_service import apply_pending_downgrade
    apply_pending_downgrade(tenant)

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )
    count = (await db.execute(
        select(func.count()).where(Lead.tenant_id == tenant_id, Lead.created_at >= month_start)
    )).scalar() or 0
    if count >= tenant.max_leads_mes:
        raise ConflictError(f"Max leads ({tenant.max_leads_mes}) reached for plan {tenant.plan}")


async def update_lead(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    data: dict,
) -> Lead:
    """Update lead fields (NOT estado — use transition_estado)."""
    if data.get("asignado_a") is not None:
        await crud.require_exists(db, Usuario, tenant_id, data["asignado_a"], label="Usuario")
    return await crud.update_fields(db, Lead, tenant_id, lead_id, data, label="Lead")


async def transition_estado(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    target_estado: str,
) -> Lead:
    """FSM transition: validates via LeadEstado.can_transition_to."""
    lead = await get_lead(db, tenant_id, lead_id)
    current = LeadEstado(lead.estado)
    target = LeadEstado(target_estado)

    if not current.can_transition_to(target):
        raise InvalidTransitionError(current.value, target.value)

    lead.estado = target.value
    await db.flush()
    return lead


async def list_leads_by_estado(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    estado: str,
    pagination: PaginationParams,
) -> PaginatedResponse:
    """List leads filtered by estado."""
    return await list_leads(db, tenant_id, pagination, estado=estado)


