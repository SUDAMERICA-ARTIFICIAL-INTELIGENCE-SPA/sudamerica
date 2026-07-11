"""Mesa service: CRUD del recurso físico reservable (mesa/silla/box…)."""

from datetime import date, datetime, time, timedelta
import secrets
import uuid

from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.mesa import Mesa
from shared.rubros import tipo_recurso_default
from app.models.reservacion import Reservacion
from app.services.tenant_rubro import load_tenant_rubro
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud
from shared.utils.exceptions import ConflictError, NotFoundError

_AVAILABILITY_SLOT_MINUTES = 90


def _availability_slot_end(hora: time) -> time:
    """Compute the requested slot end using the 90-minute reservation window."""
    return (
        datetime.combine(date.today(), hora)
        + timedelta(minutes=_AVAILABILITY_SLOT_MINUTES)
    ).time()


async def _occupied_mesa_ids(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fecha: date,
    hora: time,
) -> set[uuid.UUID]:
    requested_end = _availability_slot_end(hora)
    result = await db.execute(
        select(Reservacion.mesa_id).where(
            Reservacion.tenant_id == tenant_id,
            Reservacion.activo.is_(True),
            Reservacion.fecha_reserva == fecha,
            Reservacion.mesa_id.is_not(None),
            Reservacion.estado != "CANCELADA",
            Reservacion.hora_inicio < requested_end,
            Reservacion.hora_fin > hora,
        )
    )
    return {
        mesa_id for mesa_id in result.scalars().all()
        if mesa_id is not None
    }


def _serialize_available_mesa(mesa: Mesa) -> dict:
    """Serialize mesa availability in both new and legacy-compatible shapes."""
    return {
        "id": mesa.id,
        "mesa_id": mesa.id,
        "numero": mesa.numero,
        "capacidad": mesa.capacidad,
        "zona": mesa.nombre,
    }


async def list_mesas(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    *,
    sucursal_id: uuid.UUID | None = None,
) -> PaginatedResponse:
    """List active mesas for a tenant, optionally filtered by sucursal."""
    filters = []
    if sucursal_id is not None:
        filters.append(Mesa.sucursal_id == sucursal_id)
    return await crud.list_active(
        db, Mesa, tenant_id, pagination,
        extra_filters=filters, order_by=Mesa.numero.asc(),
    )


async def get_mesa(
    db: AsyncSession, tenant_id: uuid.UUID, mesa_id: uuid.UUID
) -> Mesa:
    """Get a single active mesa."""
    return await crud.get_by_id(db, Mesa, tenant_id, mesa_id, label="Mesa")


async def create_mesa(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Mesa:
    """Create a new mesa, enforcing unique numero per tenant."""
    existing = await db.execute(
        select(Mesa).where(
            Mesa.tenant_id == tenant_id,
            Mesa.numero == data["numero"],
            Mesa.activo.is_(True),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"Mesa con numero {data['numero']} ya existe para este tenant"
        )

    data["qr_token"] = secrets.token_hex(16)
    if not data.get("tipo"):
        # F5: tipo de recurso derivado del rubro (restaurante → "mesa", byte-idéntico).
        data["tipo"] = tipo_recurso_default(await load_tenant_rubro(db, tenant_id))
    mesa = Mesa(tenant_id=tenant_id, **data)
    db.add(mesa)
    await db.flush()
    return mesa


async def get_mesa_by_qr_token(db: AsyncSession, qr_token: str) -> dict | None:
    """Lookup mesa + sucursal + tenant by QR token.

    The caller must enable the public QR lookup context before executing this
    query so the LEFT JOIN to sucursales works under RLS.
    """
    result = await db.execute(
        sql_text(
            "SELECT m.id, m.numero, m.nombre, m.tenant_id, m.sucursal_id, m.activo, "
            "s.nombre AS sucursal_nombre, t.nombre AS tenant_nombre "
            "FROM mesas m "
            "LEFT JOIN sucursales s ON s.id = m.sucursal_id "
            "JOIN tenants t ON t.id = m.tenant_id "
            "WHERE m.qr_token = :token"
        ),
        {"token": qr_token},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def regenerate_qr_token(
    db: AsyncSession, tenant_id: uuid.UUID, mesa_id: uuid.UUID
) -> Mesa:
    """Generate a new QR token for a mesa (invalidates old QR codes)."""
    mesa = await crud.get_by_id(db, Mesa, tenant_id, mesa_id, label="Mesa")
    mesa.qr_token = secrets.token_hex(16)
    await db.flush()
    return mesa


async def update_mesa(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    mesa_id: uuid.UUID,
    data: dict,
) -> Mesa:
    """Update mesa fields."""
    return await crud.update_fields(db, Mesa, tenant_id, mesa_id, data, label="Mesa")


async def soft_delete_mesa(
    db: AsyncSession, tenant_id: uuid.UUID, mesa_id: uuid.UUID
) -> Mesa:
    """Soft-delete a mesa by setting activo=False."""
    return await crud.soft_delete(db, Mesa, tenant_id, mesa_id, label="Mesa")


async def list_available_mesas(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    fecha: date,
    hora: time,
    personas: int,
) -> list[dict]:
    """List active mesas with enough capacity that do not overlap the requested slot."""
    occupied_ids = await _occupied_mesa_ids(db, tenant_id, fecha, hora)
    stmt = (
        select(Mesa)
        .where(
            Mesa.tenant_id == tenant_id,
            Mesa.activo.is_(True),
            Mesa.capacidad >= personas,
        )
        .order_by(Mesa.capacidad.asc(), Mesa.numero.asc())
    )
    if occupied_ids:
        stmt = stmt.where(~Mesa.id.in_(occupied_ids))
    mesas = (await db.execute(stmt)).scalars().all()
    return [_serialize_available_mesa(mesa) for mesa in mesas]
