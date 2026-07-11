"""Tests for delivery assignment system: repartidores CRUD, atomic claim, FSM, payment."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.comanda import Comanda
from app.models.delivery import DeliveryAssignment, Repartidor
from app.services import delivery_svc
from shared.models.enums import DeliveryEstado

from .conftest import TENANT_ID, TestSessionFactory


# ── Helpers ───────────────────────────────────────────────────────────

TENANT_UUID = uuid.UUID(TENANT_ID)


@pytest_asyncio.fixture
async def _seed_comanda():
    """Create a test comanda for delivery assignment tests."""
    comanda_id = uuid.uuid4()
    async with TestSessionFactory() as session:
        comanda = Comanda(
            id=comanda_id,
            tenant_id=TENANT_UUID,
            tipo_entrega="DELIVERY",
            estado="PENDIENTE",
            canal_origen="WHATSAPP",
            direccion_entrega="Av. Test 1234",
            metodo_pago="EFECTIVO",
            pago_confirmado=False,
        )
        session.add(comanda)
        await session.commit()
    yield comanda_id
    # Cleanup
    async with TestSessionFactory() as session:
        await session.execute(
            select(DeliveryAssignment).where(DeliveryAssignment.comanda_id == comanda_id)
        )
        from sqlalchemy import delete
        await session.execute(delete(DeliveryAssignment).where(DeliveryAssignment.comanda_id == comanda_id))
        await session.execute(delete(Comanda).where(Comanda.id == comanda_id))
        await session.commit()


# ── Repartidor CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_repartidor():
    async with TestSessionFactory() as session:
        rep = await delivery_svc.create_repartidor(
            session, TENANT_UUID, {"nombre": "Carlos", "phone": "56911111111"},
        )
        await session.commit()
    assert rep.nombre == "Carlos"
    assert rep.phone == "56911111111"
    assert rep.tenant_id == TENANT_UUID

    # Cleanup
    async with TestSessionFactory() as session:
        from sqlalchemy import delete
        await session.execute(delete(Repartidor).where(Repartidor.id == rep.id))
        await session.commit()


@pytest.mark.asyncio
async def test_list_repartidores():
    async with TestSessionFactory() as session:
        rep = await delivery_svc.create_repartidor(
            session, TENANT_UUID, {"nombre": "Maria", "phone": "56922222222"},
        )
        await session.commit()

    async with TestSessionFactory() as session:
        reps = await delivery_svc.list_repartidores(session, TENANT_UUID, activo=True)
    assert any(r.phone == "56922222222" for r in reps)

    # Cleanup
    async with TestSessionFactory() as session:
        from sqlalchemy import delete
        await session.execute(delete(Repartidor).where(Repartidor.id == rep.id))
        await session.commit()


@pytest.mark.asyncio
async def test_get_repartidor_by_phone():
    async with TestSessionFactory() as session:
        rep = await delivery_svc.create_repartidor(
            session, TENANT_UUID, {"nombre": "Pedro", "phone": "56933333333"},
        )
        await session.commit()

    async with TestSessionFactory() as session:
        found = await delivery_svc.get_repartidor_by_phone(session, TENANT_UUID, "56933333333")
    assert found is not None
    assert found.nombre == "Pedro"

    async with TestSessionFactory() as session:
        not_found = await delivery_svc.get_repartidor_by_phone(session, TENANT_UUID, "56999999999")
    assert not_found is None

    # Cleanup
    async with TestSessionFactory() as session:
        from sqlalchemy import delete
        await session.execute(delete(Repartidor).where(Repartidor.id == rep.id))
        await session.commit()


# ── DeliveryAssignment ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_assignment(_seed_comanda):
    comanda_id = _seed_comanda
    async with TestSessionFactory() as session:
        assignment = await delivery_svc.create_assignment(
            session, TENANT_UUID, comanda_id,
            metodo_pago="EFECTIVO", monto_a_cobrar=15000,
        )
        await session.commit()

    assert assignment.comanda_id == comanda_id
    assert assignment.estado == DeliveryEstado.PUBLICADO
    assert assignment.metodo_pago == "EFECTIVO"
    assert float(assignment.monto_a_cobrar) == 15000


@pytest.mark.asyncio
async def test_claim_delivery_success(_seed_comanda):
    comanda_id = _seed_comanda
    # Create assignment
    async with TestSessionFactory() as session:
        await delivery_svc.create_assignment(session, TENANT_UUID, comanda_id)
        await session.commit()

    # Claim it
    async with TestSessionFactory() as session:
        assignment = await delivery_svc.claim_delivery(
            session, TENANT_UUID, comanda_id,
            repartidor_phone="56944444444", repartidor_nombre="Juan",
        )
        await session.commit()

    assert assignment is not None
    assert assignment.estado == DeliveryEstado.ACEPTADO
    assert assignment.repartidor_phone == "56944444444"
    assert assignment.repartidor_nombre == "Juan"
    assert assignment.claimed_at is not None


@pytest.mark.asyncio
async def test_claim_delivery_double_claim_rejected(_seed_comanda):
    comanda_id = _seed_comanda
    # Create assignment
    async with TestSessionFactory() as session:
        await delivery_svc.create_assignment(session, TENANT_UUID, comanda_id)
        await session.commit()

    # First claim succeeds
    async with TestSessionFactory() as session:
        first = await delivery_svc.claim_delivery(
            session, TENANT_UUID, comanda_id,
            repartidor_phone="56955555555",
        )
        await session.commit()
    assert first is not None

    # Second claim fails (returns None)
    async with TestSessionFactory() as session:
        second = await delivery_svc.claim_delivery(
            session, TENANT_UUID, comanda_id,
            repartidor_phone="56966666666",
        )
    assert second is None


@pytest.mark.asyncio
async def test_delivery_fsm_transitions(_seed_comanda):
    comanda_id = _seed_comanda
    async with TestSessionFactory() as session:
        assignment = await delivery_svc.create_assignment(session, TENANT_UUID, comanda_id)
        await session.commit()

    # Claim
    async with TestSessionFactory() as session:
        await delivery_svc.claim_delivery(
            session, TENANT_UUID, comanda_id, repartidor_phone="56977777777",
        )
        await session.commit()

    # Get assignment ID
    async with TestSessionFactory() as session:
        assignment = await delivery_svc.get_assignment(session, TENANT_UUID, comanda_id)
    assignment_id = assignment.id

    # ACEPTADO → EN_RUTA
    async with TestSessionFactory() as session:
        updated = await delivery_svc.transition_delivery_estado(
            session, TENANT_UUID, assignment_id, "EN_RUTA",
        )
        await session.commit()
    assert updated.estado == DeliveryEstado.EN_RUTA
    assert updated.picked_up_at is not None

    # EN_RUTA → ENTREGADO
    async with TestSessionFactory() as session:
        updated = await delivery_svc.transition_delivery_estado(
            session, TENANT_UUID, assignment_id, "ENTREGADO",
        )
        await session.commit()
    assert updated.estado == DeliveryEstado.ENTREGADO
    assert updated.delivered_at is not None


@pytest.mark.asyncio
async def test_delivery_invalid_transition(_seed_comanda):
    comanda_id = _seed_comanda
    async with TestSessionFactory() as session:
        await delivery_svc.create_assignment(session, TENANT_UUID, comanda_id)
        await session.commit()

    async with TestSessionFactory() as session:
        assignment = await delivery_svc.get_assignment(session, TENANT_UUID, comanda_id)

    # PUBLICADO → ENTREGADO should fail (must go through ACEPTADO first)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        async with TestSessionFactory() as session:
            await delivery_svc.transition_delivery_estado(
                session, TENANT_UUID, assignment.id, "ENTREGADO",
            )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_confirm_payment(_seed_comanda):
    comanda_id = _seed_comanda
    async with TestSessionFactory() as session:
        assignment = await delivery_svc.create_assignment(
            session, TENANT_UUID, comanda_id, metodo_pago="EFECTIVO",
        )
        await session.commit()

    # Confirm payment
    async with TestSessionFactory() as session:
        result = await delivery_svc.confirm_payment(session, TENANT_UUID, assignment.id)
        await session.commit()

    assert result is not None
    # Verify comanda's pago_confirmado is now True
    async with TestSessionFactory() as session:
        comanda_row = await session.execute(
            select(Comanda).where(Comanda.id == comanda_id)
        )
        comanda = comanda_row.scalar_one()
    assert comanda.pago_confirmado is True


@pytest.mark.asyncio
async def test_list_pending_assignments(_seed_comanda):
    comanda_id = _seed_comanda
    async with TestSessionFactory() as session:
        await delivery_svc.create_assignment(session, TENANT_UUID, comanda_id)
        await session.commit()

    async with TestSessionFactory() as session:
        pending = await delivery_svc.list_pending_assignments(session, TENANT_UUID)
    assert any(a.comanda_id == comanda_id for a in pending)


# ── Enum Tests ───────────────────────────────────────────────────────


def test_delivery_estado_fsm():
    """DeliveryEstado FSM: valid and invalid transitions."""
    assert DeliveryEstado.PUBLICADO.can_transition_to(DeliveryEstado.ACEPTADO)
    assert DeliveryEstado.PUBLICADO.can_transition_to(DeliveryEstado.CANCELADO)
    assert not DeliveryEstado.PUBLICADO.can_transition_to(DeliveryEstado.EN_RUTA)
    assert not DeliveryEstado.PUBLICADO.can_transition_to(DeliveryEstado.ENTREGADO)

    assert DeliveryEstado.ACEPTADO.can_transition_to(DeliveryEstado.EN_RUTA)
    assert not DeliveryEstado.ACEPTADO.can_transition_to(DeliveryEstado.PUBLICADO)

    assert DeliveryEstado.EN_RUTA.can_transition_to(DeliveryEstado.ENTREGADO)
    assert not DeliveryEstado.EN_RUTA.can_transition_to(DeliveryEstado.PUBLICADO)

    assert not DeliveryEstado.ENTREGADO.can_transition_to(DeliveryEstado.PUBLICADO)
    assert not DeliveryEstado.CANCELADO.can_transition_to(DeliveryEstado.PUBLICADO)


def test_metodo_pago_enum():
    from shared.models.enums import MetodoPago
    assert MetodoPago.TRANSFERENCIA.value == "TRANSFERENCIA"
    assert MetodoPago.EFECTIVO.value == "EFECTIVO"
    assert MetodoPago.TARJETA.value == "TARJETA"
    assert MetodoPago.CONTRA_ENTREGA.value == "CONTRA_ENTREGA"
