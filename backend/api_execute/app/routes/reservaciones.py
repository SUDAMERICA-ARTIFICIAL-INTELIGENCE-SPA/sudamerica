"""Reservacion routes: CRUD + availability check for restaurant reservations."""

import asyncio
import logging
from datetime import date, time
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse

from app.routes.deps import AdminWriter, AnyAuthenticated, MesaReader, get_user_sucursal_id
from app.services.reservacion_notify import (
    notify_reservation_confirmed,
    send_reservation_reminders,
)

logger = logging.getLogger(__name__)
from app.schemas.reservacion import (
    DisponibilidadResponse,
    MesaDisponible,
    ReservacionCreate,
    ReservacionResponse,
    ReservacionUpdate,
)
from app.services import reservacion_svc

router = APIRouter(prefix="/reservaciones", tags=["reservaciones"])


@router.get("/disponibilidad", response_model=DisponibilidadResponse)
async def check_availability(
    fecha: date = Query(...),
    hora: time = Query(...),
    cantidad_personas: int = Query(..., ge=1, le=50),
    duracion_horas: int = Query(default=2, ge=1, le=6),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Check which mesas are available for a given date, time, and party size."""
    tenant_id = current_user["tenant_id"]
    mesas = await reservacion_svc.check_availability(
        db, tenant_id, fecha, hora, cantidad_personas, duracion_horas,
    )
    return DisponibilidadResponse(
        disponible=len(mesas) > 0,
        mesas=[
            MesaDisponible(
                mesa_id=m["id"], numero=m["numero"],
                nombre=m.get("nombre"), capacidad=m["capacidad"],
            )
            for m in mesas
        ],
        fecha=fecha,
        hora=hora,
    )


@router.get("", response_model=PaginatedResponse[ReservacionResponse])
async def list_reservaciones(
    fecha: date | None = Query(default=None),
    estado: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List reservations with optional date/status filters."""
    tenant_id = current_user["tenant_id"]
    rows, total = await reservacion_svc.list_reservaciones(
        db, tenant_id, fecha=fecha, estado=estado, page=page, page_size=page_size,
        sucursal_id=get_user_sucursal_id(current_user),
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": [ReservacionResponse.model_validate(r) for r in rows],
        "meta": {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages},
    }


@router.post("", response_model=ReservacionResponse, status_code=status.HTTP_201_CREATED)
async def create_reservacion(
    body: ReservacionCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new reservation."""
    tenant_id = current_user["tenant_id"]
    reservacion = await reservacion_svc.create_reservacion(
        db, tenant_id, body.model_dump(),
    )
    await db.commit()
    return ReservacionResponse.model_validate(reservacion)


@router.get("/{reservacion_id}", response_model=ReservacionResponse)
async def get_reservacion(
    reservacion_id: UUID,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Get a single reservation."""
    tenant_id = current_user["tenant_id"]
    return ReservacionResponse.model_validate(
        await reservacion_svc.get_reservacion(db, tenant_id, reservacion_id),
    )


@router.patch("/{reservacion_id}", response_model=ReservacionResponse)
async def update_reservacion(
    reservacion_id: UUID,
    body: ReservacionUpdate,
    request: Request,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a reservation."""
    tenant_id = current_user["tenant_id"]
    reservacion = await reservacion_svc.update_reservacion(
        db, tenant_id, reservacion_id, body.model_dump(exclude_unset=True),
    )
    await db.commit()

    # Notify customer via WhatsApp when reservation is CONFIRMED
    if body.estado == "CONFIRMADA" and reservacion.telefono:
        settings = request.app.state.settings
        asyncio.create_task(
            notify_reservation_confirmed(
                settings,
                tenant_id,
                reservacion.telefono,
                reservacion.nombre_cliente,
                str(reservacion.fecha_reserva),
                reservacion.hora_inicio.strftime("%H:%M"),
                reservacion.cantidad_personas,
            )
        )

    return ReservacionResponse.model_validate(reservacion)


@router.post("/send-reminders")
async def trigger_reminders(
    request: Request,
    hours_ahead: int = Query(default=2, ge=1, le=24),
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Send WhatsApp reminders for upcoming reservations.

    Can be triggered manually or by Cloud Scheduler cron job.
    """
    settings = request.app.state.settings
    result = await send_reservation_reminders(settings, db, hours_ahead=hours_ahead)
    return result


@router.delete("/{reservacion_id}", response_model=ReservacionResponse)
async def cancel_reservacion(
    reservacion_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a reservation."""
    tenant_id = current_user["tenant_id"]
    reservacion = await reservacion_svc.cancel_reservacion(db, tenant_id, reservacion_id)
    await db.commit()
    return ReservacionResponse.model_validate(reservacion)
