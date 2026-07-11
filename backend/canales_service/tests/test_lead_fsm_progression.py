"""Tests for lead FSM auto-progression NUEVO → CONTACTADO after AI reply."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.whatsapp_service import _progress_lead_estado
from .conftest import TEST_SETTINGS, TENANT_ID


@pytest.mark.asyncio
async def test_progress_lead_nuevo_to_contactado():
    """Lead in estado NUEVO should be PATCHed to CONTACTADO."""
    lead_id = uuid.uuid4()

    # Mock GET /leads/{id} returning estado=NUEVO
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"data": {"id": str(lead_id), "estado": "NUEVO"}}

    # Mock PATCH /leads/{id}
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    patch_resp.json.return_value = {"data": {"id": str(lead_id), "estado": "CONTACTADO"}}

    call_log = []

    async def mock_get(self, path, **kwargs):
        call_log.append(("GET", path))
        return get_resp

    async def mock_patch(self, path, **kwargs):
        call_log.append(("PATCH", path, kwargs.get("json")))
        return patch_resp

    with patch("app.services.whatsapp_service.HttpClient.get", mock_get), \
         patch("app.services.whatsapp_service.HttpClient.patch", mock_patch):
        await _progress_lead_estado(
            lead_id, TENANT_ID, TEST_SETTINGS,
            {"Authorization": "Bearer test", "X-Tenant-ID": str(TENANT_ID)},
        )

    # Should have called GET then PATCH
    assert len(call_log) == 2
    assert call_log[0][0] == "GET"
    assert call_log[1][0] == "PATCH"
    assert call_log[1][2] == {"estado": "CONTACTADO"}


@pytest.mark.asyncio
async def test_progress_lead_already_contactado_skips_patch():
    """Lead already in estado CONTACTADO should NOT be PATCHed."""
    lead_id = uuid.uuid4()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"data": {"id": str(lead_id), "estado": "CONTACTADO"}}

    call_log = []

    async def mock_get(self, path, **kwargs):
        call_log.append(("GET", path))
        return get_resp

    async def mock_patch(self, path, **kwargs):
        call_log.append(("PATCH", path))
        return MagicMock(status_code=200)

    with patch("app.services.whatsapp_service.HttpClient.get", mock_get), \
         patch("app.services.whatsapp_service.HttpClient.patch", mock_patch):
        await _progress_lead_estado(
            lead_id, TENANT_ID, TEST_SETTINGS,
            {"Authorization": "Bearer test", "X-Tenant-ID": str(TENANT_ID)},
        )

    # Should have called GET but NOT PATCH
    assert len(call_log) == 1
    assert call_log[0][0] == "GET"


@pytest.mark.asyncio
async def test_progress_lead_handles_api_failure_gracefully():
    """Lead FSM progression should not raise on API failure."""
    lead_id = uuid.uuid4()

    async def mock_get(self, path, **kwargs):
        raise RuntimeError("Connection refused")

    with patch("app.services.whatsapp_service.HttpClient.get", mock_get):
        # Should not raise
        await _progress_lead_estado(
            lead_id, TENANT_ID, TEST_SETTINGS,
            {"Authorization": "Bearer test", "X-Tenant-ID": str(TENANT_ID)},
        )
