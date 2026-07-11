"""Tests for all metrica endpoints."""

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.comanda import Comanda, ComandaItem
from app.models.lead import Lead
from app.models.producto import Producto
from app.models.venta import Venta

from .conftest import TestSessionFactory

from .test_comandas import _create_comanda, _create_producto, _transition_estado


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_metricas_data():
    """Isolate metrica tests from persisted data created by earlier modules."""
    async def _purge() -> None:
        async with TestSessionFactory() as session:
            await session.execute(delete(Venta))
            await session.execute(delete(ComandaItem))
            await session.execute(delete(Comanda))
            await session.execute(delete(Lead))
            await session.execute(delete(Producto))
            await session.commit()

    await _purge()
    yield
    await _purge()


@pytest.mark.asyncio
async def test_revenue(client, auth_headers):
    resp = await client.get("/api/v1/core/metricas/revenue", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "total_ventas" in data


@pytest.mark.asyncio
async def test_operativo_summary_uses_delivered_sales(client, auth_headers):
    prod = await _create_producto(client, auth_headers, "Milanesa", "7000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"], cantidad=2)
    comanda_id = create_resp.json()["id"]

    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    await _transition_estado(client, auth_headers, comanda_id, "ENTREGADO")

    resp = await client.get("/api/v1/core/metricas/operativo?period=day", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["revenue_total"] == pytest.approx(14000.0)
    assert data["pedidos_entregados"] >= 1
    assert data["items_vendidos"] >= 2
    assert data["ticket_promedio"] >= 14000.0


@pytest.mark.asyncio
async def test_por_canal(client, auth_headers):
    # Create a lead with canal
    await client.post("/api/v1/core/leads", json={
        "nombre": "Canal Test",
        "canal": "WHATSAPP",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/core/metricas/por-canal", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_por_sector(client, auth_headers):
    await client.post("/api/v1/core/leads", json={
        "nombre": "Sector Test",
        "sector": "Tecnologia",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/core/metricas/por-sector", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_productos_top(client, auth_headers):
    resp = await client.get("/api/v1/core/metricas/productos-top", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_conversion(client, auth_headers):
    resp = await client.get("/api/v1/core/metricas/conversion", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_leads" in data
    assert "convertidos" in data
    assert "tasa_conversion" in data


@pytest.mark.asyncio
async def test_leads_estado(client, auth_headers):
    resp = await client.get("/api/v1/core/metricas/leads-estado", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_ai_metrics_real_data(client, auth_headers):
    """Dashboard AI metrics should come from real conversation data, not hardcoded."""
    resp = await client.get("/api/v1/core/metricas/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    # All AI metric fields must be present
    assert "ia_atendidas" in data
    assert "ia_mensajes" in data
    assert "ia_auto_resueltas" in data
    assert "ia_tasa_auto_resolucion" in data
    assert "ia_total_tokens" in data
    assert "ia_costo_tokens_usd" in data
    assert "ia_costo_por_conversacion" in data
    assert "ia_horas_ahorradas" in data
    assert "ahorro_ia_usd" in data
    assert "ia_roi" in data

    # With no AI conversation data, all AI metrics should be zero
    assert data["ia_atendidas"] == 0
    assert data["ia_auto_resueltas"] == 0
    assert data["ia_tasa_auto_resolucion"] == 0.0
    assert data["ia_costo_tokens_usd"] == 0.0
    assert data["ia_horas_ahorradas"] == 0.0
    assert data["ahorro_ia_usd"] == 0.0
    assert data["ia_roi"] == 0.0
