"""Tests for menu import — CSV parsing, AI extraction, route validation."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.services.menu_import_svc import (
    _parse_ai_response,
    confirm_import,
    import_from_csv,
)


# ── _parse_ai_response ──────────────────────────────────────────

def test_parse_clean_json():
    text = '{"items": [{"nombre": "Pizza", "precio": 5990, "categoria": "Pizzas", "descripcion": null}]}'
    items = _parse_ai_response(text)
    assert len(items) == 1
    assert items[0]["nombre"] == "Pizza"
    assert items[0]["precio"] == 5990


def test_parse_markdown_fences():
    text = '```json\n{"items": [{"nombre": "Sushi", "precio": 8000, "categoria": "Japonés", "descripcion": "Rolls variados"}]}\n```'
    items = _parse_ai_response(text)
    assert len(items) == 1
    assert items[0]["nombre"] == "Sushi"


def test_parse_prose_wrapped():
    text = 'Here is the menu:\n{"items": [{"nombre": "Empanada", "precio": 1500, "categoria": "Entradas", "descripcion": null}]}\nDone.'
    items = _parse_ai_response(text)
    assert len(items) == 1
    assert items[0]["nombre"] == "Empanada"


def test_parse_invalid_json():
    text = "This is not valid JSON"
    items = _parse_ai_response(text)
    assert items == []


def test_parse_empty_items():
    text = '{"items": []}'
    items = _parse_ai_response(text)
    assert items == []


# ── import_from_csv ──────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock async session."""
    db = AsyncMock()
    # Mock existing categories query
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_csv_import_basic(mock_db):
    """Test basic CSV with nombre,precio,categoria columns."""
    csv_content = b"nombre,precio,categoria\nHamburguesa,5990,Platos de Fondo\nCoca-Cola,1500,Bebidas"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 2
    assert result["categories_created"] == 2
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_csv_import_alt_columns(mock_db):
    """Test CSV with alternative column names (name, price, category)."""
    csv_content = b"name,price,category\nPizza Margherita,7990,Pizzas"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 1
    assert result["categories_created"] == 1


@pytest.mark.asyncio
async def test_csv_import_empty(mock_db):
    """Test empty CSV returns error."""
    csv_content = b"nombre,precio\n"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 0
    assert "CSV vacío" in result["errors"][0]


@pytest.mark.asyncio
async def test_csv_import_with_bom(mock_db):
    """Test CSV with UTF-8 BOM."""
    csv_content = b"\xef\xbb\xbfnombre,precio,categoria\nLasagna,8500,Pastas"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 1


@pytest.mark.asyncio
async def test_csv_import_price_cleaning(mock_db):
    """Test price with $ sign and thousands separator."""
    csv_content = b"nombre,precio\nPlato Caro,$12.990\nPlato Barato,$990"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 2


@pytest.mark.asyncio
async def test_csv_import_default_category(mock_db):
    """Test CSV without category column defaults to General."""
    csv_content = b"nombre,precio\nAgua,500"
    tenant_id = uuid4()
    result = await import_from_csv(csv_content, tenant_id, mock_db)

    assert result["created"] == 1
    assert result["categories_created"] == 1


# ── confirm_import: RLS context reapplied after _bulk_create commit ──────


@pytest.mark.asyncio
async def test_confirm_import_reapplies_tenant_context_after_bulk_create():
    """Regression: prod 500 on 2026-04-18 raised StaleDataError because
    `_bulk_create` commits → `SET LOCAL app.current_tenant_id` is cleared →
    the subsequent UPDATE on `menu_imports` matches 0 rows under RLS.

    `confirm_import` must call `set_tenant_context` again after `_bulk_create`
    returns, so the UPDATE finds the row.
    """
    tenant_id = uuid4()
    import_id = uuid4()

    record = MagicMock()
    record.status = "PENDING"
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = record

    db = AsyncMock()
    db.execute.return_value = select_result
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    fake_bulk = AsyncMock(return_value={"created": 1, "categories_created": 0, "errors": []})
    fake_set_ctx = AsyncMock()

    with patch("app.services.menu_import_svc._bulk_create", fake_bulk), \
         patch("app.services.menu_import_svc.set_tenant_context", fake_set_ctx):
        result = await confirm_import(import_id, [{"nombre": "X", "precio": 1000}], tenant_id, db)

    assert result["created"] == 1
    fake_bulk.assert_awaited_once()
    fake_set_ctx.assert_awaited_once_with(db, str(tenant_id))
    assert record.status == "CONFIRMED"
