"""Tests for image storage service and product image upload."""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.image_storage_svc import (
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_SIZE,
    _to_webp,
    download_image,
)

from app.services.web_scraper_svc import (
    _extract_image_urls,
    _extract_category_names,
    fuzzy_match_image,
    validate_url,
)


# ── URL Validation ──────────────────────────────────────────────

def test_validate_url_https():
    assert validate_url("https://example.com/carta") == "https://example.com/carta"


def test_validate_url_upgrades_http():
    result = validate_url("http://example.com/menu")
    assert result.startswith("https://")


def test_validate_url_rejects_private_ip():
    with pytest.raises(ValueError, match="privadas"):
        validate_url("https://192.168.1.1/menu")


def test_validate_url_rejects_localhost():
    with pytest.raises(ValueError, match="privadas"):
        validate_url("https://localhost/menu")


def test_validate_url_rejects_ftp():
    with pytest.raises(ValueError, match="HTTP/HTTPS"):
        validate_url("ftp://example.com/menu")


def test_validate_url_rejects_empty_domain():
    with pytest.raises(ValueError):
        validate_url("https:///path")


# ── Image URL Extraction ────────────────────────────────────────

def test_extract_image_urls_basic():
    html = '''<img src="https://cdn.example.com/pizza.jpg" alt="Pizza Margherita">'''
    result = _extract_image_urls(html, "https://example.com")
    assert "Pizza Margherita" in result
    assert result["Pizza Margherita"] == "https://cdn.example.com/pizza.jpg"


def test_extract_image_urls_relative():
    html = '''<img src="/images/sushi.jpg" alt="Sushi Roll">'''
    result = _extract_image_urls(html, "https://example.com")
    assert result["Sushi Roll"] == "https://example.com/images/sushi.jpg"


def test_extract_image_urls_skips_logos():
    html = '''<img src="/logo.png" alt="Logo"><img src="/food.jpg" alt="Hamburguesa">'''
    result = _extract_image_urls(html, "https://example.com")
    assert "Logo" not in result
    assert "Hamburguesa" in result


def test_extract_image_urls_skips_no_alt():
    html = '''<img src="/food.jpg" alt=""><img src="/food2.jpg" alt="Pizza">'''
    result = _extract_image_urls(html, "https://example.com")
    assert len(result) == 1
    assert "Pizza" in result


def test_extract_image_urls_protocol_relative():
    html = '''<img src="//cdn.example.com/img.jpg" alt="Plato">'''
    result = _extract_image_urls(html, "https://example.com")
    assert result["Plato"] == "https://cdn.example.com/img.jpg"


# ── Category Name Extraction ────────────────────────────────────

def test_extract_category_names():
    html = '''<button role="tab">Pizzas</button><button role="tab">Bebidas</button>'''
    names = _extract_category_names(html)
    assert "Pizzas" in names
    assert "Bebidas" in names


def test_extract_category_names_deduplicates():
    html = '''<button role="tab">Pizzas</button><button role="tab">Pizzas</button>'''
    names = _extract_category_names(html)
    assert names.count("Pizzas") == 1


# ── Fuzzy Match ──────────────────────────────────────────────────

def test_fuzzy_match_exact():
    image_map = {"Pizza Margherita": "https://cdn.example.com/pizza.jpg"}
    assert fuzzy_match_image("Pizza Margherita", image_map) == "https://cdn.example.com/pizza.jpg"


def test_fuzzy_match_contains():
    image_map = {"Pizza Margherita Especial": "https://cdn.example.com/pizza.jpg"}
    assert fuzzy_match_image("Pizza Margherita", image_map) == "https://cdn.example.com/pizza.jpg"


def test_fuzzy_match_word_overlap():
    image_map = {"Margherita Premium con Albahaca": "https://cdn.example.com/marg.jpg"}
    assert fuzzy_match_image("Margherita Premium", image_map) == "https://cdn.example.com/marg.jpg"


def test_fuzzy_match_no_match():
    image_map = {"Sushi Roll": "https://cdn.example.com/sushi.jpg"}
    assert fuzzy_match_image("Hamburguesa", image_map) is None


def test_fuzzy_match_empty_map():
    assert fuzzy_match_image("Pizza", {}) is None


def test_fuzzy_match_case_insensitive():
    image_map = {"PIZZA MARGHERITA": "https://cdn.example.com/pizza.jpg"}
    assert fuzzy_match_image("pizza margherita", image_map) == "https://cdn.example.com/pizza.jpg"


# ── Image Storage Service ────────────────────────────────────────

def test_to_webp_fallback_no_pillow():
    """If Pillow is not available, _to_webp returns original bytes."""
    # Pass invalid image bytes — should return them unchanged (Pillow will fail)
    fake_bytes = b"not-a-real-image"
    result = _to_webp(fake_bytes)
    assert result == fake_bytes


def test_allowed_image_types():
    assert "image/png" in ALLOWED_IMAGE_TYPES
    assert "image/jpeg" in ALLOWED_IMAGE_TYPES
    assert "image/webp" in ALLOWED_IMAGE_TYPES
    assert "application/pdf" not in ALLOWED_IMAGE_TYPES


def test_max_image_size():
    assert MAX_IMAGE_SIZE == 5 * 1024 * 1024


# ── Upload validation (unit, no GCS) ─────────────────────────────

@pytest.mark.asyncio
async def test_upload_rejects_invalid_type():
    from app.services.image_storage_svc import upload_product_image
    with pytest.raises(ValueError, match="no soportado"):
        await upload_product_image(
            tenant_id=uuid4(),
            producto_id=uuid4(),
            file_content=b"fake",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_upload_rejects_oversized():
    from app.services.image_storage_svc import upload_product_image
    big_content = b"x" * (MAX_IMAGE_SIZE + 1)
    with pytest.raises(ValueError, match="grande"):
        await upload_product_image(
            tenant_id=uuid4(),
            producto_id=uuid4(),
            file_content=big_content,
            content_type="image/jpeg",
        )
