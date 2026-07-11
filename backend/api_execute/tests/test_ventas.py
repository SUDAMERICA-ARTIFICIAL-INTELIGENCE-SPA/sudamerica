"""Tests for ventas: create with immutable total, list, get."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.venta import Venta



@pytest.mark.asyncio
async def test_create_venta_immutable_total(client, auth_headers):
    # Create a producto first
    prod = await client.post("/api/v1/core/productos", json={
        "nombre": "VentaProd",
        "precio": "100.00",
    }, headers=auth_headers)
    prod_id = prod.json()["id"]

    resp = await client.post("/api/v1/core/ventas", json={
        "producto_id": prod_id,
        "cantidad": 3,
        "precio_unitario": "100.00",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    # total = 3 * 100.00 = 300.00 (computed server-side)
    assert Decimal(str(data["total"])) == Decimal("300.00")
    assert data["cantidad"] == 3


@pytest.mark.asyncio
async def test_list_ventas(client, auth_headers):
    resp = await client.get("/api/v1/core/ventas", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_list_ventas_filters_by_date(client, auth_headers, db_session):
    prod = await client.post("/api/v1/core/productos", json={
        "nombre": "VentaFechaProd",
        "precio": "80.00",
    }, headers=auth_headers)
    prod_id = prod.json()["id"]

    older = await client.post("/api/v1/core/ventas", json={
        "producto_id": prod_id,
        "cantidad": 1,
        "precio_unitario": "80.00",
    }, headers=auth_headers)
    newer = await client.post("/api/v1/core/ventas", json={
        "producto_id": prod_id,
        "cantidad": 2,
        "precio_unitario": "80.00",
    }, headers=auth_headers)

    older_id = uuid.UUID(older.json()["id"])
    older_row = await db_session.get(Venta, older_id)
    older_row.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    await db_session.commit()

    fecha_desde = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = await client.get(
        f"/api/v1/core/ventas?fecha_desde={fecha_desde}",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    ids = [venta["id"] for venta in resp.json()["data"]]
    assert newer.json()["id"] in ids
    assert older.json()["id"] not in ids


@pytest.mark.asyncio
async def test_get_venta(client, auth_headers):
    prod = await client.post("/api/v1/core/productos", json={
        "nombre": "GetVentaProd",
        "precio": "50.00",
    }, headers=auth_headers)
    prod_id = prod.json()["id"]

    create = await client.post("/api/v1/core/ventas", json={
        "producto_id": prod_id,
        "cantidad": 2,
        "precio_unitario": "50.00",
    }, headers=auth_headers)
    venta_id = create.json()["id"]

    resp = await client.get(f"/api/v1/core/ventas/{venta_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == venta_id
    assert Decimal(str(resp.json()["total"])) == Decimal("100.00")
