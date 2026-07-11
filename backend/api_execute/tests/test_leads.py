"""Tests for leads: CRUD + FSM transitions (valid, invalid, full funnel, filters)."""

import pytest

from .conftest import TENANT_ID


@pytest.mark.asyncio
async def test_create_lead(client, auth_headers):
    resp = await client.post("/api/v1/core/leads", json={
        "nombre": "Juan Perez",
        "email": "juan@example.com",
        "canal": "WHATSAPP",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Juan Perez"
    assert data["estado"] == "NUEVO"


@pytest.mark.asyncio
async def test_list_leads(client, auth_headers):
    await client.post("/api/v1/core/leads", json={
        "nombre": "Maria Lopez",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/core/leads", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_lead(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "Carlos Diaz",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    resp = await client.get(f"/api/v1/core/leads/{lead_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Carlos Diaz"


@pytest.mark.asyncio
async def test_valid_transition_nuevo_to_contactado(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "FSM Test",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    resp = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "CONTACTADO",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "CONTACTADO"


@pytest.mark.asyncio
async def test_invalid_transition_nuevo_to_convertido(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "Invalid FSM",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    resp = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "CONVERTIDO",
    }, headers=auth_headers)
    assert resp.status_code == 422
    assert "INVALID_TRANSITION" in resp.json().get("code", "")


@pytest.mark.asyncio
async def test_full_funnel_nuevo_to_convertido(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "Full Funnel",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    # NUEVO -> CONTACTADO
    r1 = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "CONTACTADO",
    }, headers=auth_headers)
    assert r1.status_code == 200

    # CONTACTADO -> EN_PROCESO
    r2 = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "EN_PROCESO",
    }, headers=auth_headers)
    assert r2.status_code == 200

    # EN_PROCESO -> CONVERTIDO
    r3 = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "CONVERTIDO",
    }, headers=auth_headers)
    assert r3.status_code == 200
    assert r3.json()["estado"] == "CONVERTIDO"


@pytest.mark.asyncio
async def test_convertido_is_terminal(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "Terminal Test",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    for estado in ["CONTACTADO", "EN_PROCESO", "CONVERTIDO"]:
        await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
            "estado": estado,
        }, headers=auth_headers)

    # CONVERTIDO -> anything should fail
    resp = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "DESCARTADO",
    }, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_descartado_is_terminal(client, auth_headers):
    create = await client.post("/api/v1/core/leads", json={
        "nombre": "Descartado Terminal",
    }, headers=auth_headers)
    lead_id = create.json()["id"]

    await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "DESCARTADO",
    }, headers=auth_headers)

    resp = await client.patch(f"/api/v1/core/leads/{lead_id}/estado", json={
        "estado": "CONTACTADO",
    }, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_filter_leads_by_estado(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/leads/estado/NUEVO", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    for item in data["data"]:
        assert item["estado"] == "NUEVO"
