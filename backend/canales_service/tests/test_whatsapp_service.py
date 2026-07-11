"""Unit tests for whatsapp_service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.whatsapp_service import _normalize_phone, process_incoming

from .conftest import TEST_SETTINGS


def test_normalize_phone_strips_suffix():
    assert _normalize_phone("5491155551234@s.whatsapp.net") == "5491155551234"


def test_normalize_phone_plain_number():
    assert _normalize_phone("5491155551234") == "5491155551234"


@pytest.mark.asyncio
async def test_unknown_instance_returns_ignored():
    db = AsyncMock()
    data = {
        "instance_name": "unknown-instance",
        "sender": "5491155551234@s.whatsapp.net",
        "message": "Hola",
    }

    with patch(
        "app.services.whatsapp_service.instance_service.lookup_by_instance_name",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await process_incoming(data, TEST_SETTINGS, db)

    assert result["status"] == "ignored"
    assert result["reason"] == "unknown_instance"


@pytest.mark.asyncio
async def test_tenant_id_comes_from_db_not_instance_name():
    other_tid = uuid.UUID("99999999-9999-9999-9999-999999999999")
    instance = MagicMock()
    instance.tenant_id = other_tid
    instance.instance_name = "custom-name"
    db = AsyncMock()
    data = {
        "instance_name": "custom-name",
        "sender": "5491155551234@s.whatsapp.net",
        "message": "Hola",
    }
    lead_id = str(uuid.uuid4())
    mock_ai_resp = MagicMock()
    mock_ai_resp.status_code = 200
    mock_ai_resp.json.return_value = {"response": ""}
    mock_ai_resp.raise_for_status = MagicMock()
    mock_lead_search_resp = MagicMock()
    mock_lead_search_resp.status_code = 200
    mock_lead_search_resp.json.return_value = {"data": [{"id": lead_id}]}
    captured_headers = {}

    async def mock_post(self, path, **kwargs):
        if "/process-message" in path or "/chat" in path:
            captured_headers.update(kwargs.get("headers", {}))
            return mock_ai_resp
        return mock_lead_search_resp

    async def mock_get(self, path, **kwargs):
        return mock_lead_search_resp

    with (
        patch(
            "app.services.whatsapp_service.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=instance,
        ),
        patch("app.services.whatsapp_service.HttpClient.post", mock_post),
        patch("app.services.whatsapp_service.HttpClient.get", mock_get),
    ):
        await process_incoming(data, TEST_SETTINGS, db)

    assert captured_headers.get("X-Tenant-ID") == str(other_tid)
