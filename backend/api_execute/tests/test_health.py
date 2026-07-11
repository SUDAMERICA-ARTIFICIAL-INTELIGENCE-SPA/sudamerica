"""Tests for health endpoints."""

import pytest


@pytest.mark.asyncio
async def test_liveness(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "api_execute"


@pytest.mark.asyncio
async def test_readiness(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "api_execute"
