"""Tests for productos: CRUD + filters + reactivar."""

import pytest

from .conftest import TENANT_ID


@pytest.mark.asyncio
async def test_create_producto(client, auth_headers):
    resp = await client.post("/api/v1/core/productos", json={
        "nombre": "Laptop",
        "precio": "1200.00",
        "stock": 10,
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Laptop"
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_list_productos(client, auth_headers):
    await client.post("/api/v1/core/productos", json={
        "nombre": "Mouse",
        "precio": "25.00",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/core/productos", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_filter_productos_by_nombre(client, auth_headers):
    await client.post("/api/v1/core/productos", json={
        "nombre": "Teclado Gamer",
        "precio": "80.00",
    }, headers=auth_headers)

    resp = await client.get(
        "/api/v1/core/productos?nombre=Teclado", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1
    assert any("Teclado" in item["nombre"] for item in data["data"])


@pytest.mark.asyncio
async def test_filter_productos_by_precio(client, auth_headers):
    await client.post("/api/v1/core/productos", json={
        "nombre": "Monitor",
        "precio": "500.00",
    }, headers=auth_headers)

    resp = await client.get(
        "/api/v1/core/productos?precio_min=400&precio_max=600",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_update_producto(client, auth_headers):
    create = await client.post("/api/v1/core/productos", json={
        "nombre": "OldName",
        "precio": "10.00",
    }, headers=auth_headers)
    prod_id = create.json()["id"]

    resp = await client.patch(f"/api/v1/core/productos/{prod_id}", json={
        "nombre": "NewName",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "NewName"


@pytest.mark.asyncio
async def test_soft_delete_producto(client, auth_headers):
    create = await client.post("/api/v1/core/productos", json={
        "nombre": "DeleteMe",
        "precio": "5.00",
    }, headers=auth_headers)
    prod_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/core/productos/{prod_id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/core/productos/{prod_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_reactivar_producto(client, auth_headers):
    create = await client.post("/api/v1/core/productos", json={
        "nombre": "ReactivateMe",
        "precio": "15.00",
    }, headers=auth_headers)
    prod_id = create.json()["id"]

    await client.delete(f"/api/v1/core/productos/{prod_id}", headers=auth_headers)

    resp = await client.patch(
        f"/api/v1/core/productos/{prod_id}/activar", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["activo"] is True


@pytest.mark.asyncio
async def test_create_producto_disponible_default(client, auth_headers):
    """New products should default to disponible=True."""
    resp = await client.post("/api/v1/core/productos", json={
        "nombre": "Hamburguesa",
        "precio": "8500.00",
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["disponible"] is True


@pytest.mark.asyncio
async def test_toggle_disponible_via_patch(client, auth_headers):
    """PATCH disponible=false should toggle availability."""
    create = await client.post("/api/v1/core/productos", json={
        "nombre": "Pan de Papa",
        "precio": "2000.00",
    }, headers=auth_headers)
    prod_id = create.json()["id"]
    assert create.json()["disponible"] is True

    resp = await client.patch(f"/api/v1/core/productos/{prod_id}", json={
        "disponible": False,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["disponible"] is False

    # Toggle back
    resp = await client.patch(f"/api/v1/core/productos/{prod_id}", json={
        "disponible": True,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["disponible"] is True


@pytest.mark.asyncio
async def test_filter_productos_by_disponible(client, auth_headers):
    """GET ?disponible=true should filter products."""
    create1 = await client.post("/api/v1/core/productos", json={
        "nombre": "Plato A",
        "precio": "100.00",
    }, headers=auth_headers)
    create2 = await client.post("/api/v1/core/productos", json={
        "nombre": "Plato B",
        "precio": "200.00",
    }, headers=auth_headers)
    prod_b_id = create2.json()["id"]
    await client.patch(f"/api/v1/core/productos/{prod_b_id}", json={
        "disponible": False,
    }, headers=auth_headers)

    resp = await client.get(
        "/api/v1/core/productos?disponible=true", headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # All returned products should be disponible
    assert all(item["disponible"] is True for item in data["data"])
