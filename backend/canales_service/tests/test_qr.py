"""Tests for QR routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from .conftest import TENANT_ID

TENANT_ID_STR = str(TENANT_ID)


@pytest.mark.asyncio
async def test_generate_qr_success(
    client,
    auth_headers,
    mock_evolution_create_instance,
):
    mock_register = AsyncMock()
    mock_lookup = AsyncMock(return_value=None)
    mock_update = AsyncMock()

    with (
        patch("app.services.qr_service.HttpClient.post", return_value=mock_evolution_create_instance),
        patch(
            "app.services.qr_service.get_qr_code_with_retry",
            new_callable=AsyncMock,
            return_value={"base64": "AAAA"},
        ),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock) as ensure_webhook,
        patch("app.routes.qr.instance_service.lookup_by_instance_name", mock_lookup),
        patch("app.routes.qr.instance_service.register_instance", mock_register),
        patch("app.routes.qr.instance_service.update_status", mock_update),
    ):
        response = await client.post(
            f"/api/v1/canales/qr/{TENANT_ID_STR}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["qr_code"] == "data:image/png;base64,AAAA"
    assert data["instance_name"] == f"tenant-{TENANT_ID_STR}"
    assert data["status"] == "pending"
    ensure_webhook.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_qr_already_connected(
    client,
    auth_headers,
    mock_evolution_status,
    mock_evolution_instance,
):
    schedule_mock = patch("app.routes.qr._schedule_history_sync")
    with (
        patch("app.services.qr_service.HttpClient.get", return_value=mock_evolution_status),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock) as ensure_webhook,
        patch(
            "app.routes.qr.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
        patch("app.routes.qr.instance_service.update_status", new_callable=AsyncMock),
        schedule_mock as schedule_sync,
    ):
        response = await client.post(
            f"/api/v1/canales/qr/{TENANT_ID_STR}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "open"
    assert data["qr_code"] == ""
    schedule_sync.assert_called_once()
    ensure_webhook.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_qr_cross_tenant_forbidden(client, other_tenant_auth_headers):
    response = await client.post(
        f"/api/v1/canales/qr/{TENANT_ID_STR}",
        headers=other_tenant_auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_qr_status_success(client, auth_headers, mock_evolution_status, mock_evolution_instance):
    schedule_mock = patch("app.routes.qr._schedule_history_sync")
    with (
        patch("app.services.qr_service.HttpClient.get", return_value=mock_evolution_status),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock) as ensure_webhook,
        patch(
            "app.routes.qr.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
        patch("app.routes.qr.instance_service.update_status", new_callable=AsyncMock),
        schedule_mock as schedule_sync,
    ):
        response = await client.get(
            f"/api/v1/canales/qr/{TENANT_ID_STR}/status",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "open"
    assert data["instance_name"] == f"tenant-{TENANT_ID_STR}"
    schedule_sync.assert_called_once()
    ensure_webhook.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_qr_status_does_not_resync_recently_synced_instance(
    client,
    auth_headers,
    mock_evolution_status,
    mock_evolution_instance,
):
    mock_evolution_instance.status = "CONNECTED_SYNCED"
    mock_evolution_instance.updated_at = datetime.now(UTC)
    update_mock = AsyncMock()
    schedule_mock = patch("app.routes.qr._schedule_history_sync")

    with (
        patch("app.services.qr_service.HttpClient.get", return_value=mock_evolution_status),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock) as ensure_webhook,
        patch(
            "app.routes.qr.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
        patch("app.routes.qr.instance_service.update_status", update_mock),
        schedule_mock as schedule_sync,
    ):
        response = await client.get(
            f"/api/v1/canales/qr/{TENANT_ID_STR}/status",
            headers=auth_headers,
        )

    assert response.status_code == 200
    schedule_sync.assert_not_called()
    update_mock.assert_not_awaited()
    ensure_webhook.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_qr_status_requeues_recent_sync_for_stale_synced_instance(
    client,
    auth_headers,
    mock_evolution_status,
    mock_evolution_instance,
):
    mock_evolution_instance.status = "CONNECTED_SYNCED"
    mock_evolution_instance.updated_at = datetime.now(UTC) - timedelta(hours=12)
    update_mock = AsyncMock()
    schedule_mock = patch("app.routes.qr._schedule_history_sync")

    with (
        patch("app.services.qr_service.HttpClient.get", return_value=mock_evolution_status),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock) as ensure_webhook,
        patch(
            "app.routes.qr.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
        patch("app.routes.qr.instance_service.update_status", update_mock),
        schedule_mock as schedule_sync,
    ):
        response = await client.get(
            f"/api/v1/canales/qr/{TENANT_ID_STR}/status",
            headers=auth_headers,
        )

    assert response.status_code == 200
    ensure_webhook.assert_awaited_once()
    update_mock.assert_awaited_once()
    schedule_sync.assert_called_once()


@pytest.mark.asyncio
async def test_get_qr_status_returns_open_when_db_persist_fails(
    client,
    auth_headers,
    mock_evolution_status,
):
    schedule_mock = patch("app.routes.qr._schedule_history_sync")

    with (
        patch("app.services.qr_service.HttpClient.get", return_value=mock_evolution_status),
        patch(
            "app.routes.qr._mark_connected_and_queue_sync",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db unavailable"),
        ),
        schedule_mock as schedule_sync,
    ):
        response = await client.get(
            f"/api/v1/canales/qr/{TENANT_ID_STR}/status",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "open"
    schedule_sync.assert_called_once()


@pytest.mark.asyncio
async def test_register_cloud_api_success(
    client,
    auth_headers,
    mock_evolution_create_instance,
):
    """Test Cloud API instance registration (no QR scan needed)."""
    mock_register_fn = AsyncMock()

    with (
        patch("app.services.qr_service.HttpClient.post", return_value=mock_evolution_create_instance),
        patch("app.services.qr_service.ensure_webhook", new_callable=AsyncMock),
        patch("app.routes.qr.instance_service.get_instance_for_tenant", new_callable=AsyncMock, return_value=None),
        patch("app.routes.qr._register_cloud_api_instance", mock_register_fn),
    ):
        response = await client.post(
            f"/api/v1/canales/cloud-api/{TENANT_ID_STR}",
            headers=auth_headers,
            json={
                "meta_token": "EAAtest123permanent",
                "meta_number_id": "123456789",
                "meta_business_id": "987654321",
                "phone_number": "+56912345678",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["instance_name"] == f"tenant-{TENANT_ID_STR}"
    assert data["status"] == "CONNECTED"
    assert data["integration"] == "WHATSAPP-BUSINESS"
    assert data["phone_number"] == "+56912345678"


@pytest.mark.asyncio
async def test_register_cloud_api_cross_tenant_forbidden(client, other_tenant_auth_headers):
    """Cloud API registration should be forbidden for other tenants."""
    response = await client.post(
        f"/api/v1/canales/cloud-api/{TENANT_ID_STR}",
        headers=other_tenant_auth_headers,
        json={
            "meta_token": "EAAtest123",
            "meta_number_id": "123456789",
            "meta_business_id": "987654321",
        },
    )
    assert response.status_code == 403
