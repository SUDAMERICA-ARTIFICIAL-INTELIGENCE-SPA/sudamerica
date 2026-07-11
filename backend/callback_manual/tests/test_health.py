"""Tests for health-check endpoints."""

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_health(client):
    """GET /health returns 200 with service name."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "callback_manual"


@pytest.mark.asyncio
async def test_health_ready(client):
    """GET /health/ready returns 200 when DB is reachable."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "callback_manual"
