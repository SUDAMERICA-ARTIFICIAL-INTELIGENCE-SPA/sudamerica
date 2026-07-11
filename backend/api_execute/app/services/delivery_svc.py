"""Delivery service — repartidor CRUD + delivery assignment claim logic."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.delivery import DeliveryAssignment, Repartidor
from shared.database import set_tenant_context
from shared.models.enums import DeliveryEstado

logger = logging.getLogger(__name__)


async def _ensure_tenant_context(db: AsyncSession, tenant_id: UUID) -> None:
    await set_tenant_context(db, str(tenant_id))


# ── Repartidor CRUD ───────────────────────────────────────────────────


async def create_repartidor(
    db: AsyncSession, tenant_id: UUID, data: dict,
) -> Repartidor:
    await _ensure_tenant_context(db, tenant_id)
    repartidor = Repartidor(tenant_id=tenant_id, **data)
    db.add(repartidor)
    await db.flush()
    await db.refresh(repartidor)
    return repartidor


async def list_repartidores(
    db: AsyncSession, tenant_id: UUID, activo: bool | None = True,
) -> list[Repartidor]:
    await _ensure_tenant_context(db, tenant_id)
    stmt = select(Repartidor).where(Repartidor.tenant_id == tenant_id)
    if activo is not None:
        stmt = stmt.where(Repartidor.activo == activo)
    stmt = stmt.order_by(Repartidor.nombre)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_repartidor_by_phone(
    db: AsyncSession, tenant_id: UUID, phone: str,
) -> Repartidor | None:
    await _ensure_tenant_context(db, tenant_id)
    stmt = select(Repartidor).where(
        and_(Repartidor.tenant_id == tenant_id, Repartidor.phone == phone)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── DeliveryAssignment ────────────────────────────────────────────────


async def create_assignment(
    db: AsyncSession,
    tenant_id: UUID,
    comanda_id: UUID,
    metodo_pago: str | None = None,
    monto_a_cobrar: float = 0,
) -> DeliveryAssignment:
    """Create a delivery assignment in PUBLICADO state when a delivery comanda is created."""
    await _ensure_tenant_context(db, tenant_id)
    assignment = DeliveryAssignment(
        tenant_id=tenant_id,
        comanda_id=comanda_id,
        estado=DeliveryEstado.PUBLICADO,
        metodo_pago=metodo_pago,
        monto_a_cobrar=monto_a_cobrar,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    logger.info("DeliveryAssignment created: %s for comanda %s", assignment.id, comanda_id)
    return assignment


async def claim_delivery(
    db: AsyncSession,
    tenant_id: UUID,
    comanda_id: UUID,
    repartidor_phone: str,
    repartidor_nombre: str | None = None,
) -> DeliveryAssignment | None:
    """Atomically claim a delivery. Returns the assignment if claimed, None if already taken.

    Uses UPDATE ... WHERE estado = 'PUBLICADO' to prevent double-claims.
    """
    await _ensure_tenant_context(db, tenant_id)
    now = datetime.now(timezone.utc)

    # Resolve repartidor_id if phone is registered
    repartidor = await get_repartidor_by_phone(db, tenant_id, repartidor_phone)

    stmt = (
        update(DeliveryAssignment)
        .where(
            and_(
                DeliveryAssignment.comanda_id == comanda_id,
                DeliveryAssignment.tenant_id == tenant_id,
                DeliveryAssignment.estado == DeliveryEstado.PUBLICADO,
            )
        )
        .values(
            estado=DeliveryEstado.ACEPTADO,
            repartidor_phone=repartidor_phone,
            repartidor_nombre=repartidor_nombre or (repartidor.nombre if repartidor else None),
            repartidor_id=repartidor.id if repartidor else None,
            claimed_at=now,
            updated_at=now,
        )
        .returning(DeliveryAssignment.id)
    )
    result = await db.execute(stmt)
    updated_id = result.scalar_one_or_none()
    if not updated_id:
        return None

    # Also update the comanda's repartidor fields for backwards compat
    from app.models.comanda import Comanda
    comanda_update = (
        update(Comanda)
        .where(Comanda.id == comanda_id)
        .values(
            repartidor_nombre=repartidor_nombre or (repartidor.nombre if repartidor else None),
            repartidor_phone=repartidor_phone,
            updated_at=now,
        )
    )
    await db.execute(comanda_update)
    await db.flush()

    # Reload full object
    assignment = await get_assignment(db, tenant_id, comanda_id)
    logger.info("Delivery claimed: comanda=%s by phone=%s", comanda_id, repartidor_phone)
    return assignment


async def get_assignment(
    db: AsyncSession, tenant_id: UUID, comanda_id: UUID,
) -> DeliveryAssignment | None:
    await _ensure_tenant_context(db, tenant_id)
    stmt = select(DeliveryAssignment).where(
        and_(
            DeliveryAssignment.comanda_id == comanda_id,
            DeliveryAssignment.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_assignment_by_id(
    db: AsyncSession, tenant_id: UUID, assignment_id: UUID,
) -> DeliveryAssignment | None:
    await _ensure_tenant_context(db, tenant_id)
    stmt = select(DeliveryAssignment).where(
        and_(
            DeliveryAssignment.id == assignment_id,
            DeliveryAssignment.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def transition_delivery_estado(
    db: AsyncSession, tenant_id: UUID, assignment_id: UUID, new_estado: str,
) -> DeliveryAssignment | None:
    """Transition delivery assignment state with FSM validation."""
    await _ensure_tenant_context(db, tenant_id)
    assignment = await get_assignment_by_id(db, tenant_id, assignment_id)
    if not assignment:
        return None

    current = DeliveryEstado(assignment.estado)
    target = DeliveryEstado(new_estado)
    if not current.can_transition_to(target):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid delivery transition: {current.value} -> {target.value}",
        )

    now = datetime.now(timezone.utc)
    values: dict = {"estado": target.value, "updated_at": now}
    if target == DeliveryEstado.EN_RUTA:
        values["picked_up_at"] = now
    elif target == DeliveryEstado.ENTREGADO:
        values["delivered_at"] = now

    stmt = (
        update(DeliveryAssignment)
        .where(DeliveryAssignment.id == assignment_id)
        .values(**values)
    )
    await db.execute(stmt)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def confirm_payment(
    db: AsyncSession, tenant_id: UUID, assignment_id: UUID,
) -> DeliveryAssignment | None:
    """Driver confirms payment received — sets pago_confirmado=True on the comanda."""
    await _ensure_tenant_context(db, tenant_id)
    assignment = await get_assignment_by_id(db, tenant_id, assignment_id)
    if not assignment:
        return None

    from app.models.comanda import Comanda
    now = datetime.now(timezone.utc)
    stmt = (
        update(Comanda)
        .where(and_(Comanda.id == assignment.comanda_id, Comanda.tenant_id == tenant_id))
        .values(pago_confirmado=True, updated_at=now)
    )
    await db.execute(stmt)
    await db.flush()
    return assignment


async def list_pending_assignments(
    db: AsyncSession, tenant_id: UUID,
) -> list[DeliveryAssignment]:
    """List delivery assignments in PUBLICADO state (unclaimed)."""
    await _ensure_tenant_context(db, tenant_id)
    stmt = (
        select(DeliveryAssignment)
        .where(
            and_(
                DeliveryAssignment.tenant_id == tenant_id,
                DeliveryAssignment.estado == DeliveryEstado.PUBLICADO,
            )
        )
        .order_by(DeliveryAssignment.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_latest_publicado_for_group(
    db: AsyncSession, tenant_id: UUID,
) -> DeliveryAssignment | None:
    """Find the most recent PUBLICADO delivery assignment for a tenant.

    Used when a driver says 'TOMO' in the group — they claim the latest pending delivery.
    """
    await _ensure_tenant_context(db, tenant_id)
    stmt = (
        select(DeliveryAssignment)
        .where(
            and_(
                DeliveryAssignment.tenant_id == tenant_id,
                DeliveryAssignment.estado == DeliveryEstado.PUBLICADO,
            )
        )
        .order_by(DeliveryAssignment.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
