"""Tests for the POST /api/v1/tasks/retry-failed endpoint."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from .conftest import TENANT_ID, TEST_SETTINGS, _make_token
from shared.models.enums import RevisionDeliveryStatus


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_make_token()}",
        "X-Tenant-ID": str(TENANT_ID),
    }


@pytest_asyncio.fixture()
async def client():
    with patch("app.config.TasksSettings", return_value=TEST_SETTINGS):
        from app.main import create_app
        from shared.database.dependencies import get_db

        app = create_app()
        app.state.settings = TEST_SETTINGS
        mock_db = AsyncMock()

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


@pytest.mark.asyncio
async def test_retry_failed_endpoint_exists(client, auth_headers):
    """Verify the retry-failed endpoint is registered and accepts POST."""
    with patch(
        "app.services.send_response_service.retry_failed_deliveries",
        new_callable=AsyncMock,
        return_value={"retried": 0, "succeeded": 0, "still_failed": 0},
    ):
        resp = await client.post(
            "/api/v1/tasks/retry-failed",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "retried" in data
    assert "succeeded" in data
    assert "still_failed" in data


@pytest.mark.asyncio
async def test_retry_failed_requires_auth(client):
    """Retry-failed endpoint requires authentication."""
    resp = await client.post("/api/v1/tasks/retry-failed")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_retry_failed_calls_service(client, auth_headers):
    """Retry-failed endpoint delegates to send_response_service."""
    mock_retry = AsyncMock(
        return_value={"retried": 3, "succeeded": 2, "still_failed": 1}
    )
    with patch(
        "app.services.send_response_service.retry_failed_deliveries",
        mock_retry,
    ):
        resp = await client.post(
            "/api/v1/tasks/retry-failed",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["retried"] == 3
    assert data["succeeded"] == 2
    assert data["still_failed"] == 1
    mock_retry.assert_called_once()
