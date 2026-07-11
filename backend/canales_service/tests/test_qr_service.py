"""Unit tests for qr_service contract helpers."""

from unittest.mock import MagicMock, patch

import pytest
from app.services import qr_service

from .conftest import TEST_SETTINGS


def test_create_payload_uses_v2_contract():
    payload = qr_service._create_payload("tenant-test", "+56 9 1234 5678")

    assert payload["integration"] == "WHATSAPP-BAILEYS"
    assert payload["qrcode"] is True
    assert payload["number"] == "56912345678"


@pytest.mark.asyncio
async def test_get_qr_code_renders_png_base64():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"code": "scan-me"}

    with patch("app.services.qr_service.HttpClient.get", return_value=response):
        data = await qr_service.get_qr_code("tenant-test", TEST_SETTINGS)

    assert data["base64"].startswith("iVBOR")


def test_normalize_connect_response_strips_data_url_prefix():
    data = qr_service._normalize_connect_response(
        {"base64": "data:image/png;base64,AAAA"},
    )

    assert data["base64"] == "AAAA"


@pytest.mark.asyncio
async def test_set_webhook_uses_supported_endpoint():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    captured: dict[str, object] = {}

    async def fake_post(self, path, **kwargs):
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return response

    with patch("app.services.qr_service.HttpClient.post", fake_post):
        await qr_service._set_webhook(
            qr_service.HttpClient(TEST_SETTINGS.EVOLUTION_API_URL),
            "tenant-test",
            TEST_SETTINGS,
        )

    assert captured["path"] == "/webhook/set/tenant-test"
    assert captured["json"] == qr_service._webhook_payload(TEST_SETTINGS)
    assert captured["json"]["webhook"]["webhookBase64"] is True


def test_webhook_payload_token_in_headers_not_url():
    """P0-1 Security: webhook token MUST be in headers, NOT in URL query param."""
    payload = qr_service._webhook_payload(TEST_SETTINGS)
    webhook = payload["webhook"]

    # Token must be in headers
    assert "headers" in webhook
    assert webhook["headers"]["apikey"] == TEST_SETTINGS.WEBHOOK_TOKEN

    # URL must NOT contain the token as a query param
    assert "token=" not in webhook["url"]
    assert "?" not in webhook["url"] or "token" not in webhook["url"]


def test_webhook_payload_url_is_clean():
    """Webhook URL should be the base URL without any query parameters appended."""
    payload = qr_service._webhook_payload(TEST_SETTINGS)
    assert payload["webhook"]["url"] == TEST_SETTINGS.EVOLUTION_WEBHOOK_URL
