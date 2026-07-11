"""Tests for /api/v1/core/sales-targets endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_targets_empty(client, auth_headers):
    resp = await client.get("/api/v1/core/sales-targets", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] >= 0


@pytest.mark.asyncio
async def test_create_target(client, auth_headers):
    payload = {
        "periodo": "2026-03",
        "meta_ventas": 50000,
        "meta_leads": 100,
        "meta_conversion": 25,
    }
    resp = await client.post(
        "/api/v1/core/sales-targets",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["periodo"] == "2026-03"
    assert body["meta_ventas"] == 50000


@pytest.mark.asyncio
async def test_upsert_target(client, auth_headers):
    payload = {
        "periodo": "2026-04",
        "meta_ventas": 30000,
        "meta_leads": 80,
        "meta_conversion": 20,
    }
    # Create
    resp1 = await client.post(
        "/api/v1/core/sales-targets", headers=auth_headers, json=payload
    )
    assert resp1.status_code == 201

    # Upsert (same periodo, no asesor_id)
    payload["meta_ventas"] = 60000
    resp2 = await client.post(
        "/api/v1/core/sales-targets", headers=auth_headers, json=payload
    )
    assert resp2.status_code == 201
    assert resp2.json()["meta_ventas"] == 60000


@pytest.mark.asyncio
async def test_filter_by_periodo(client, auth_headers):
    payload = {
        "periodo": "2026-05",
        "meta_ventas": 10000,
        "meta_leads": 50,
        "meta_conversion": 15,
    }
    await client.post(
        "/api/v1/core/sales-targets", headers=auth_headers, json=payload
    )
    resp = await client.get(
        "/api/v1/core/sales-targets?periodo=2026-05", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    for target in body["data"]:
        assert target["periodo"] == "2026-05"


@pytest.mark.asyncio
async def test_invalid_periodo_format(client, auth_headers):
    payload = {
        "periodo": "2026/03",
        "meta_ventas": 50000,
        "meta_leads": 100,
        "meta_conversion": 25,
    }
    resp = await client.post(
        "/api/v1/core/sales-targets", headers=auth_headers, json=payload
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_targets_requires_auth(client):
    resp = await client.get("/api/v1/core/sales-targets")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_targets_pagination(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/sales-targets?page=1&page_size=5", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 5
