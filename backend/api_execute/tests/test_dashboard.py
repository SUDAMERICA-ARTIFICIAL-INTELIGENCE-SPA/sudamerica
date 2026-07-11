"""Tests for /api/v1/core/metricas/dashboard and revenue timeseries."""

import pytest


@pytest.mark.asyncio
async def test_dashboard_kpis(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/metricas/dashboard", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "ventas_mes" in body
    assert "meta_mes" in body
    assert "nuevos_leads" in body
    assert "tasa_conversion" in body
    assert "ia_atendidas" in body
    assert "ahorro_ia_usd" in body


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    resp = await client.get("/api/v1/core/metricas/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_revenue_timeseries_day(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/metricas/revenue?period=day", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_revenue_timeseries_month(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/metricas/revenue?period=month", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_revenue_no_period_returns_totals(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/metricas/revenue", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_revenue" in body
    assert "total_ventas" in body
