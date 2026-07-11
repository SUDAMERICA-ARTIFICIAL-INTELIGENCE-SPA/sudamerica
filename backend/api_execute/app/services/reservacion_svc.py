"""Service for restaurant table reservations."""

import logging
from datetime import date, time, timedelta, datetime
from uuid import UUID

from sqlalchemy import and_, select, func, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservacion import Reservacion
from shared.utils.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)

_DEFAULT_DURATION_HOURS = 2


def _compute_hora_fin(hora_inicio: time, duracion_horas: int = _DEFAULT_DURATION_HOURS) -> time:
    """Calculate end time from start time + duration."""
    dt = datetime.combine(date.today(), hora_inicio) + timedelta(hours=duracion_horas)
    return dt.time()


async def check_availability(
    session: AsyncSession,
    tenant_id: UUID,
    fecha: date,
    hora: time,
    cantidad_personas: int,
    duracion_horas: int = _DEFAULT_DURATION_HOURS,
) -> list[dict]:
    """Find available mesas for a given date/time/party size.

    Returns list of dicts with mesa info for mesas that:
    1. Have enough capacity (capacidad >= cantidad_personas)
    2. Are not reserved at the requested time slot
    """
    hora_fin = _compute_hora_fin(hora, duracion_horas)

    # Get all active mesas with sufficient capacity
    all_mesas = await session.execute(
        sql_text(
            "SELECT id, numero, nombre, capacidad FROM mesas "
            "WHERE tenant_id = :tid AND activo = true AND capacidad >= :cap "
            "ORDER BY capacidad, numero"
        ),
        {"tid": str(tenant_id), "cap": cantidad_personas},
    )
    mesas = [dict(r) for r in all_mesas.mappings().all()]

    if not mesas:
        return []

    # Get mesas already reserved at the requested time (overlapping reservations)
    reserved = await session.execute(
        sql_text(
            "SELECT DISTINCT mesa_id FROM reservaciones "
            "WHERE tenant_id = :tid AND fecha_reserva = :fecha "
            "AND activo = true AND estado NOT IN ('CANCELADA') "
            "AND hora_inicio < :hora_fin AND hora_fin > :hora_inicio"
        ),
        {
            "tid": str(tenant_id),
            "fecha": fecha,
            "hora_inicio": hora,
            "hora_fin": hora_fin,
        },
    )
    reserved_ids = {str(r[0]) for r in reserved.all()}

    # Filter out reserved mesas
    available = [
        m for m in mesas
        if str(m["id"]) not in reserved_ids
    ]

    return available


async def _verify_mesa_available(
    session: AsyncSession, tenant_id: UUID, data: dict,
) -> None:
    """Raise ConflictError if the specified mesa is not available."""
    available = await check_availability(
        session, tenant_id,
        data["fecha_reserva"], data["hora_inicio"],
        data["cantidad_personas"],
    )
    available_ids = {str(m["id"]) for m in available}
    if str(data["mesa_id"]) not in available_ids:
        raise ConflictError("La mesa seleccionada no está disponible en ese horario")


async def _auto_assign_mesa(
    session: AsyncSession, tenant_id: UUID, reservacion: Reservacion, data: dict,
) -> None:
    """Assign the best-fit available mesa if none was specified."""
    available = await check_availability(
        session, tenant_id,
        data["fecha_reserva"], data["hora_inicio"],
        data["cantidad_personas"],
    )
    if available:
        reservacion.mesa_id = available[0]["id"]
        await session.flush()


def _build_reservacion(tenant_id: UUID, data: dict, hora_fin: time) -> Reservacion:
    """Construct a Reservacion model from input data."""
    return Reservacion(
        tenant_id=tenant_id,
        lead_id=data.get("lead_id"),
        mesa_id=data.get("mesa_id"),
        fecha_reserva=data["fecha_reserva"],
        hora_inicio=data["hora_inicio"],
        hora_fin=hora_fin,
        cantidad_personas=data["cantidad_personas"],
        nombre_cliente=data["nombre_cliente"],
        rut=data.get("rut"),
        email=data.get("email"),
        telefono=data.get("telefono"),
        estado="PENDIENTE",
        notas=data.get("notas"),
    )


async def create_reservacion(
    session: AsyncSession,
    tenant_id: UUID,
    data: dict,
) -> Reservacion:
    """Create a new reservation after checking availability."""
    hora_fin = data.get("hora_fin") or _compute_hora_fin(data["hora_inicio"])

    if data.get("mesa_id"):
        await _verify_mesa_available(session, tenant_id, data)

    reservacion = _build_reservacion(tenant_id, data, hora_fin)
    session.add(reservacion)
    await session.flush()

    if not data.get("mesa_id"):
        await _auto_assign_mesa(session, tenant_id, reservacion, data)

    logger.info(
        "Reservation created: %s for %s on %s at %s (%d people, mesa=%s)",
        reservacion.id, data["nombre_cliente"], data["fecha_reserva"],
        data["hora_inicio"], data["cantidad_personas"], reservacion.mesa_id,
    )
    return reservacion


async def list_reservaciones(
    session: AsyncSession,
    tenant_id: UUID,
    fecha: date | None = None,
    estado: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sucursal_id: UUID | None = None,
) -> tuple[list[Reservacion], int]:
    """List reservations with optional filters, optionally scoped by sucursal."""
    conditions = [
        Reservacion.tenant_id == tenant_id,
        Reservacion.activo.is_(True),
    ]
    if sucursal_id is not None:
        conditions.append(Reservacion.sucursal_id == sucursal_id)
    if fecha:
        conditions.append(Reservacion.fecha_reserva == fecha)
    if estado:
        conditions.append(Reservacion.estado == estado)

    total = (await session.execute(
        select(func.count(Reservacion.id)).where(*conditions)
    )).scalar() or 0

    rows = (await session.execute(
        select(Reservacion)
        .where(*conditions)
        .order_by(Reservacion.fecha_reserva.desc(), Reservacion.hora_inicio)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return list(rows), total


async def get_reservacion(
    session: AsyncSession,
    tenant_id: UUID,
    reservacion_id: UUID,
) -> Reservacion:
    """Get a single reservation."""
    row = (await session.execute(
        select(Reservacion).where(
            Reservacion.id == reservacion_id,
            Reservacion.tenant_id == tenant_id,
            Reservacion.activo.is_(True),
        )
    )).scalar_one_or_none()
    if not row:
        raise NotFoundError("Reservacion", str(reservacion_id))
    return row


async def update_reservacion(
    session: AsyncSession,
    tenant_id: UUID,
    reservacion_id: UUID,
    data: dict,
) -> Reservacion:
    """Update a reservation."""
    reservacion = await get_reservacion(session, tenant_id, reservacion_id)
    for key, value in data.items():
        if value is not None and hasattr(reservacion, key):
            setattr(reservacion, key, value)
    await session.flush()
    return reservacion


async def cancel_reservacion(
    session: AsyncSession,
    tenant_id: UUID,
    reservacion_id: UUID,
) -> Reservacion:
    """Cancel a reservation."""
    reservacion = await get_reservacion(session, tenant_id, reservacion_id)
    if reservacion.estado == "CANCELADA":
        raise ConflictError("La reservación ya está cancelada")
    reservacion.estado = "CANCELADA"
    await session.flush()
    logger.info("Reservation %s cancelled", reservacion_id)
    return reservacion
