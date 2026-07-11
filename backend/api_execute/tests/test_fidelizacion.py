"""Tests for fidelización service — lead stats after comanda delivery."""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria
from app.models.comanda import Comanda, ComandaItem
from app.models.lead import Lead
from app.models.producto import Producto
from app.services.fidelizacion_svc import compute_estado_cliente, update_lead_stats

from .conftest import TENANT_ID, TestSessionFactory

TENANT_UUID = uuid.UUID(TENANT_ID)


# ---------------------------------------------------------------------------
# Pure-logic tests for compute_estado_cliente
# ---------------------------------------------------------------------------
class TestComputeEstadoCliente:
    """Test the tier-classification helper (no DB needed)."""

    def test_zero_orders_returns_nuevo(self):
        assert compute_estado_cliente(0) == "NUEVO"

    def test_one_order_returns_nuevo(self):
        assert compute_estado_cliente(1) == "NUEVO"

    def test_two_orders_returns_ocasional(self):
        assert compute_estado_cliente(2) == "OCASIONAL"

    def test_four_orders_returns_ocasional(self):
        assert compute_estado_cliente(4) == "OCASIONAL"

    def test_five_orders_returns_frecuente(self):
        assert compute_estado_cliente(5) == "FRECUENTE"

    def test_nine_orders_returns_frecuente(self):
        assert compute_estado_cliente(9) == "FRECUENTE"

    def test_ten_orders_returns_vip(self):
        assert compute_estado_cliente(10) == "VIP"

    def test_hundred_orders_returns_vip(self):
        assert compute_estado_cliente(100) == "VIP"


# ---------------------------------------------------------------------------
# DB integration tests for update_lead_stats
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    """Seed a lead, categoria, producto, and a delivered comanda."""
    lead_id = uuid.uuid4()
    categoria_id = uuid.uuid4()
    producto_id = uuid.uuid4()
    comanda_id = uuid.uuid4()

    # Lead
    lead = Lead(
        id=lead_id,
        tenant_id=TENANT_UUID,
        nombre="Test Client",
        estado="NUEVO",
        total_pedidos=0,
        total_gastado=0,
    )
    db_session.add(lead)

    # Categoria
    cat = Categoria(
        id=categoria_id,
        tenant_id=TENANT_UUID,
        nombre="Platos de Fondo",
    )
    db_session.add(cat)

    # Producto
    producto = Producto(
        id=producto_id,
        tenant_id=TENANT_UUID,
        categoria_id=categoria_id,
        nombre="Lomo Saltado",
        precio=12500,
        stock=99,
    )
    db_session.add(producto)

    # Comanda with 2 items of the same product
    comanda = Comanda(
        id=comanda_id,
        tenant_id=TENANT_UUID,
        cliente_id=lead_id,
        tipo_entrega="MESA",
        numero_mesa=5,
        estado="ENTREGADO",
        canal_origen="WEB",
        entregado_at=datetime.now(timezone.utc),
    )
    db_session.add(comanda)
    await db_session.flush()

    item = ComandaItem(
        id=uuid.uuid4(),
        comanda_id=comanda_id,
        producto_id=producto_id,
        cantidad=2,
        precio_unitario=12500,
        modifiers_json=[],
        subtotal=25000,
    )
    db_session.add(item)
    await db_session.flush()

    # Refresh so relationships are loaded
    await db_session.refresh(comanda)
    await db_session.refresh(lead)

    return {
        "lead": lead,
        "lead_id": lead_id,
        "producto_id": producto_id,
        "comanda": comanda,
        "comanda_id": comanda_id,
    }


@pytest.mark.asyncio
async def test_update_lead_stats_first_order(db_session: AsyncSession, seed_data):
    """First delivered comanda sets correct stats on the lead."""
    data = seed_data
    comanda = data["comanda"]

    await update_lead_stats(db_session, TENANT_UUID, comanda)
    await db_session.flush()

    lead = data["lead"]
    await db_session.refresh(lead)

    assert lead.total_pedidos == 1
    assert float(lead.total_gastado) == 25000.0
    assert lead.plato_favorito == "Lomo Saltado"
    assert lead.ultima_visita == date.today()
    assert lead.estado_cliente == "NUEVO"  # 1 order → NUEVO


@pytest.mark.asyncio
async def test_update_lead_stats_no_cliente_id(db_session: AsyncSession):
    """Comanda without cliente_id should return early (no-op)."""
    comanda = Comanda(
        id=uuid.uuid4(),
        tenant_id=TENANT_UUID,
        cliente_id=None,
        tipo_entrega="DELIVERY",
        estado="ENTREGADO",
        canal_origen="WHATSAPP",
    )
    db_session.add(comanda)
    await db_session.flush()

    # Should not raise
    await update_lead_stats(db_session, TENANT_UUID, comanda)


@pytest.mark.asyncio
async def test_estado_transitions_with_multiple_orders(
    db_session: AsyncSession, seed_data
):
    """Simulate multiple orders and verify estado_cliente transitions."""
    data = seed_data
    lead = data["lead"]

    # Manually set total_pedidos to simulate prior orders, then call update
    # After update, total_pedidos will be incremented by 1

    # Simulate 1st order (start from 0)
    lead.total_pedidos = 0
    lead.total_gastado = 0
    await update_lead_stats(db_session, TENANT_UUID, data["comanda"])
    await db_session.flush()
    await db_session.refresh(lead)
    assert lead.estado_cliente == "NUEVO"  # 1 order

    # Simulate going from 1 to 2
    lead.total_pedidos = 1
    await update_lead_stats(db_session, TENANT_UUID, data["comanda"])
    await db_session.flush()
    await db_session.refresh(lead)
    assert lead.estado_cliente == "OCASIONAL"  # 2 orders

    # Simulate going from 4 to 5
    lead.total_pedidos = 4
    await update_lead_stats(db_session, TENANT_UUID, data["comanda"])
    await db_session.flush()
    await db_session.refresh(lead)
    assert lead.estado_cliente == "FRECUENTE"  # 5 orders

    # Simulate going from 9 to 10
    lead.total_pedidos = 9
    await update_lead_stats(db_session, TENANT_UUID, data["comanda"])
    await db_session.flush()
    await db_session.refresh(lead)
    assert lead.estado_cliente == "VIP"  # 10 orders


@pytest.mark.asyncio
async def test_total_gastado_accumulates(db_session: AsyncSession, seed_data):
    """total_gastado should accumulate across calls."""
    data = seed_data
    lead = data["lead"]

    lead.total_pedidos = 0
    lead.total_gastado = 5000  # Pre-existing spend

    await update_lead_stats(db_session, TENANT_UUID, data["comanda"])
    await db_session.flush()
    await db_session.refresh(lead)

    # 5000 existing + 25000 from comanda
    assert float(lead.total_gastado) == 30000.0
