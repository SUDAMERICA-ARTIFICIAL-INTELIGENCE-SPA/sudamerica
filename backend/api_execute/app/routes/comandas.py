"""Comanda routes: CRUD + FSM transitions + KDS view."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.enums import ComandaEstado
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import AdminWriter, ComandaReader, ComandaWriter, get_user_sucursal_id
from app.routes.ws_kds import broadcast_kds_event
from app.schemas.comanda import ComandaCreate, ComandaResponse, ComandaTransicion
from app.services import comanda_svc
from app.services.comanda_notify import notify_customer_state_change

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comandas", tags=["comandas"])


def _log_notify_error(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("Order notification failed: %s", task.exception())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ComandaResponse)
async def create_comanda(
    body: ComandaCreate,
    current_user: dict = ComandaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new comanda with items."""
    tenant_id = current_user["tenant_id"]
    comanda = await comanda_svc.create_comanda(db, tenant_id, body.model_dump())
    result_dict = comanda_svc.enrich_comanda(comanda)

    task = asyncio.create_task(
        broadcast_kds_event(str(tenant_id), {"type": "comanda_created", "data": result_dict})
    )
    task.add_done_callback(_log_notify_error)

    return result_dict


@router.get("", response_model=PaginatedResponse[ComandaResponse])
async def list_comandas(
    pagination: PaginationParams = Depends(),
    estado: str | None = Query(None),
    tipo_entrega: str | None = Query(None),
    canal_origen: str | None = Query(None),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    sucursal_id: UUID | None = Query(None, description="Filter by sucursal (ADMIN override)"),
    cliente_id: UUID | None = Query(None, description="Filter by lead (used for 'lo de siempre')"),
    order_desc: bool = Query(False, description="Reverse chronological order"),
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    """List comandas with optional filters. Uses explicit sucursal_id if provided, else user's assigned."""
    effective_sucursal = sucursal_id if sucursal_id else get_user_sucursal_id(current_user)
    return await comanda_svc.list_comandas(
        db, current_user["tenant_id"], pagination,
        estado=estado,
        tipo_entrega=tipo_entrega,
        canal_origen=canal_origen,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        sucursal_id=effective_sucursal,
        cliente_id=cliente_id,
        order_desc=order_desc,
    )


@router.get("/kds", response_model=dict)
async def get_kds_view(
    sucursal_id: UUID | None = Query(None, description="Filter by sucursal (ADMIN override)"),
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    """KDS view: active comandas grouped by PENDIENTE, EN_COCINA, LISTO."""
    effective_sucursal = sucursal_id if sucursal_id else get_user_sucursal_id(current_user)
    return await comanda_svc.get_kds_view(
        db, current_user["tenant_id"],
        sucursal_id=effective_sucursal,
    )


@router.get("/{comanda_id}", response_model=ComandaResponse)
async def get_comanda(
    comanda_id: UUID,
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single comanda with items."""
    comanda = await comanda_svc.get_comanda(
        db, current_user["tenant_id"], comanda_id
    )
    return comanda_svc.enrich_comanda(comanda)


@router.patch("/{comanda_id}/estado", response_model=ComandaResponse)
async def transition_comanda_estado(
    comanda_id: UUID,
    body: ComandaTransicion,
    request: Request,
    current_user: dict = ComandaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Transition comanda estado (FSM validated)."""
    tenant_id = current_user["tenant_id"]
    comanda = await comanda_svc.transition_estado(
        db,
        tenant_id,
        comanda_id,
        body.estado,
        usuario_id=current_user.get("user_id"),
    )

    # For DELIVERY orders, the final ENTREGADO notification is emitted by the
    # delivery route (PATCH /delivery/{id}/estado) so the customer doesn't
    # get two "entregado" messages. MESA/RETIRO don't go through delivery,
    # so ENTREGADO on those fires here.
    notify_states = {
        ComandaEstado.EN_COCINA.value,
        ComandaEstado.LISTO.value,
    }
    if comanda.tipo_entrega != "DELIVERY":
        notify_states.add(ComandaEstado.ENTREGADO.value)

    if (
        body.estado in notify_states
        and comanda.canal_origen == "WHATSAPP"
        and comanda.cliente
        and comanda.cliente.telefono
    ):
        settings = request.app.state.settings
        task = asyncio.create_task(
            notify_customer_state_change(
                settings,
                tenant_id,
                comanda.id,
                comanda.cliente.telefono,
                comanda.cliente.nombre,
                comanda.tipo_entrega,
                body.estado,
                prep_time_min=comanda.tiempo_estimado_min or 30,
            )
        )
        task.add_done_callback(_log_notify_error)

    result_dict = comanda_svc.enrich_comanda(comanda)

    ws_task = asyncio.create_task(
        broadcast_kds_event(str(tenant_id), {"type": "comanda_updated", "data": result_dict})
    )
    ws_task.add_done_callback(_log_notify_error)

    return result_dict


@router.delete("/{comanda_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comanda(
    comanda_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a comanda."""
    tenant_id = current_user["tenant_id"]
    await comanda_svc.soft_delete_comanda(db, tenant_id, comanda_id)

    task = asyncio.create_task(
        broadcast_kds_event(
            str(tenant_id),
            {"type": "comanda_deleted", "data": {"id": str(comanda_id)}},
        )
    )
    task.add_done_callback(_log_notify_error)
