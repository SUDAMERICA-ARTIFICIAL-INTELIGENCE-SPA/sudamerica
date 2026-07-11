"""Tests for web scraper service and URL import endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.web_scraper_svc import (
    ScrapedPage,
    _extract_category_names,
    _extract_image_urls,
    fuzzy_match_image,
    validate_url,
)
from app.services.menu_import_svc import import_from_url


# ── import_from_url ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_url_no_api_key():
    """Returns error if BROWSERLESS_API_KEY is not set."""
    settings = MagicMock()
    settings.BROWSERLESS_API_KEY = ""
    db = AsyncMock()

    result = await import_from_url("https://example.com/menu", uuid4(), db, settings)
    assert result["created"] == 0
    assert "BROWSERLESS_API_KEY" in result["errors"][0]


@pytest.mark.asyncio
async def test_import_url_invalid_url():
    """Returns error for invalid URL."""
    settings = MagicMock()
    settings.BROWSERLESS_API_KEY = "test-key"
    db = AsyncMock()

    result = await import_from_url("ftp://bad-url", uuid4(), db, settings)
    assert result["created"] == 0
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_import_url_no_screenshots():
    """Returns error when no screenshots captured."""
    settings = MagicMock()
    settings.BROWSERLESS_API_KEY = "test-key"
    settings.BROWSERLESS_TIMEOUT = 30
    db = AsyncMock()

    empty_page = ScrapedPage(screenshots=[], image_map={})

    with patch("app.services.menu_import_svc.web_scraper_svc") as mock_scraper:
        mock_scraper.render_and_extract = AsyncMock(return_value=empty_page)
        result = await import_from_url("https://example.com/menu", uuid4(), db, settings)

    assert result["created"] == 0
    assert "screenshot" in result["errors"][0].lower()


@pytest.mark.asyncio
async def test_import_url_ai_extraction():
    """Full flow with mocked Browserless + AI."""
    settings = MagicMock()
    settings.BROWSERLESS_API_KEY = "test-key"
    settings.BROWSERLESS_TIMEOUT = 30
    settings.GEMINI_API_KEY = "test-gemini"
    settings.OPENAI_API_KEY = ""
    settings.GEMINI_BASE_URL = "https://api.test.com"
    settings.GEMINI_MODEL = "gemini-test"
    settings.GCS_BUCKET_NAME = ""

    page = ScrapedPage(
        screenshots=[b"fake-png-screenshot"],
        image_map={"Pizza": "https://cdn.example.com/pizza.jpg"},
    )

    ai_response = {
        "choices": [{
            "message": {
                "content": '{"items": [{"nombre": "Pizza Margherita", "precio": 8990, "categoria": "Pizzas", "descripcion": "Tomate y queso"}]}'
            }
        }]
    }

    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_db_result
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.services.menu_import_svc.web_scraper_svc") as mock_scraper, \
         patch("app.services.menu_import_svc.httpx.AsyncClient") as mock_http:

        mock_scraper.render_and_extract = AsyncMock(return_value=page)
        mock_scraper.fuzzy_match_image = fuzzy_match_image

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ai_response
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_client

        result = await import_from_url("https://example.com/carta", uuid4(), mock_db, settings)

    assert result["created"] == 1
    assert result["categories_created"] == 1
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_import_url_private_ip_rejected():
    """Rejects private IPs (SSRF protection)."""
    settings = MagicMock()
    settings.BROWSERLESS_API_KEY = "test-key"
    db = AsyncMock()

    result = await import_from_url("https://192.168.1.1/menu", uuid4(), db, settings)
    assert result["created"] == 0
    assert "privadas" in result["errors"][0].lower() or "internas" in result["errors"][0].lower()
