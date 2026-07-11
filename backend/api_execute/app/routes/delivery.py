"""Delivery routes: driver pool CRUD + delivery assignment claim/tracking."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

from app.routes.deps import AdminWriter, ComandaReader, ComandaWriter
from app.schemas.delivery import (
    DeliveryAssignmentResponse,
    DeliveryClaimRequest,
    DeliveryEstadoUpdate,
    RepartidorCreate,
    RepartidorResponse,
    RepartidorUpdate,
)
from app.services import comanda_svc, delivery_svc
from app.services.comanda_notify import notify_customer_state_change

logger = logging.getLogger(__name__)

router = APIRouter(tags=["delivery"])


# ── Repartidores CRUD ─────────────────────────────────────────────────


@router.post(
    "/repartidores",
    status_code=status.HTTP_201_CREATED,
    response_model=RepartidorResponse,
)
async def create_repartidor(
    body: RepartidorCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(current_user["tenant_id"])
    repartidor = await delivery_svc.create_repartidor(
        db, tenant_id, body.model_dump(exclude_unset=True),
    )
    await db.commit()
    return repartidor


@router.get("/repartidores", response_model=list[RepartidorResponse])
async def list_repartidores(
    activo: bool | None = True,
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(current_user["tenant_id"])
    return await delivery_svc.list_repartidores(db, tenant_id, activo)


# ── Delivery Assignments ──────────────────────────────────────────────


@router.post(
    "/delivery/claim",
    status_code=status.HTTP_200_OK,
    response_model=DeliveryAssignmentResponse,
)
async def claim_delivery(
    body: DeliveryClaimRequest,
    current_user: dict = ComandaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Claim a delivery assignment. Returns 409 if already claimed."""
    tenant_id = UUID(current_user["tenant_id"])
    assignment = await delivery_svc.claim_delivery(
        db, tenant_id, body.comanda_id,
        body.repartidor_phone, body.repartidor_nombre,
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta entrega ya fue tomada por otro repartidor.",
        )
    await db.commit()
    return assignment


@router.get("/delivery/pending", response_model=list[DeliveryAssignmentResponse])
async def list_pending_deliveries(
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(current_user["tenant_id"])
    return await delivery_svc.list_pending_assignments(db, tenant_id)


@router.get(
    "/delivery/{assignment_id}",
    response_model=DeliveryAssignmentResponse,
)
async def get_delivery(
    assignment_id: UUID,
    current_user: dict = ComandaReader,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(current_user["tenant_id"])
    assignment = await delivery_svc.get_assignment_by_id(db, tenant_id, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Delivery assignment not found")
    return assignment


def _log_notify_error(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("Delivery notification failed: %s", task.exception())


_DELIVERY_CUSTOMER_EVENTS: dict[str, str] = {
    "EN_RUTA": "EN_RUTA",
    "ENTREGADO": "ENTREGADO",
}


@router.patch(
    "/delivery/{assignment_id}/estado",
    response_model=DeliveryAssignmentResponse,
)
async def update_delivery_estado(
    assignment_id: UUID,
    body: DeliveryEstadoUpdate,
    request: Request,
    current_user: dict = ComandaWriter,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(current_user["tenant_id"])
    assignment = await delivery_svc.transition_delivery_estado(
        db, tenant_id, assignment_id, body.estado,
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Delivery assignment not found")
    await db.commit()

    customer_event = _DELIVERY_CUSTOMER_EVENTS.get(body.estado)
    if customer_event and assignment.comanda_id:
        try:
            comanda = await comanda_svc.get_comanda(db, tenant_id, assignment.comanda_id)
        except Exception:
            comanda = None
        if (
            comanda
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
                    customer_event,
                    prep_time_min=comanda.tiempo_estimado_min or 30,
                )
            )
            task.add_done_callback(_log_notify_error)

    return assignment


@router.patch(
    "/delivery/{assignment_id}/confirm-payment",
    response_model=DeliveryAssignmentResponse,
)
async def confirm_delivery_payment(
    assignment_id: UUID,
    current_user: dict = ComandaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Driver confirms payment received for cash/card-on-delivery orders."""
    tenant_id = UUID(current_user["tenant_id"])
    assignment = await delivery_svc.confirm_payment(db, tenant_id, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Delivery assignment not found")
    await db.commit()
    return assignment
