"""Tests for categorias: CRUD + soft delete."""

import pytest

from .conftest import TENANT_ID


@pytest.mark.asyncio
async def test_create_categoria(client, auth_headers):
    resp = await client.post("/api/v1/core/categorias", json={
        "nombre": "Electrónica",
        "descripcion": "Dispositivos electrónicos",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Electrónica"
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_list_categorias(client, auth_headers):
    await client.post("/api/v1/core/categorias", json={
        "nombre": "Ropa",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/core/categorias", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert data["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_categoria(client, auth_headers):
    create = await client.post("/api/v1/core/categorias", json={
        "nombre": "Alimentos",
    }, headers=auth_headers)
    cat_id = create.json()["id"]

    resp = await client.get(f"/api/v1/core/categorias/{cat_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Alimentos"


@pytest.mark.asyncio
async def test_update_categoria(client, auth_headers):
    create = await client.post("/api/v1/core/categorias", json={
        "nombre": "Original",
    }, headers=auth_headers)
    cat_id = create.json()["id"]

    resp = await client.patch(f"/api/v1/core/categorias/{cat_id}", json={
        "nombre": "Updated",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Updated"


@pytest.mark.asyncio
async def test_soft_delete_categoria(client, auth_headers):
    create = await client.post("/api/v1/core/categorias", json={
        "nombre": "ToDelete",
    }, headers=auth_headers)
    cat_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/core/categorias/{cat_id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/core/categorias/{cat_id}", headers=auth_headers)
    assert get_resp.status_code == 404
