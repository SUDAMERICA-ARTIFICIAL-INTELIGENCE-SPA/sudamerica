"""Tests for health-check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_liveness(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "canales_service"


@pytest.mark.asyncio
async def test_health_readiness(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "canales_service"
