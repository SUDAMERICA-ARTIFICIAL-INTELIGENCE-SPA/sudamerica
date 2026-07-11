"""Tests for ai_orchestrator: media marker resolution + regression tests."""

import logging.handlers
import re
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_orchestrator import (
    _attach_image,
    _attach_menu,
    _extract_list,
    _extract_mesa_token,
    _extract_poll,
    _fetch_modifier_map,
    _resolve_media_markers,
    extract_order_json,
)


TENANT_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_attach_menu_no_marker():
    text, attachments = await _attach_menu("Hola, bienvenido!", None, TENANT_ID, None)
    assert text == "Hola, bienvenido!"
    assert attachments == []


@pytest.mark.asyncio
async def test_attach_menu_with_config_url():
    text, attachments = await _attach_menu(
        "Aqui tienes [ENVIAR_MENU] nuestro menu",
        {"menu_pdf_url": "https://example.com/menu.pdf"},
        TENANT_ID,
        None,
    )
    assert "[ENVIAR_MENU]" not in text
    assert len(attachments) == 1
    assert attachments[0]["url"] == "https://example.com/menu.pdf"
    assert attachments[0]["type"] == "document"


@pytest.mark.asyncio
async def test_attach_menu_auto_generate():
    with patch(
        "app.services.ai_orchestrator._auto_generate_menu_pdf",
        new_callable=AsyncMock,
        return_value="https://storage.example.com/auto-menu.pdf",
    ):
        text, attachments = await _attach_menu(
            "Te envio el menu [ENVIAR_MENU]", None, TENANT_ID, None,
        )
    assert "[ENVIAR_MENU]" not in text
    assert len(attachments) == 1
    assert "auto-menu.pdf" in attachments[0]["url"]


@pytest.mark.asyncio
async def test_attach_menu_no_url_available():
    with patch(
        "app.services.ai_orchestrator._auto_generate_menu_pdf",
        new_callable=AsyncMock,
        return_value=None,
    ):
        text, attachments = await _attach_menu(
            "Te envio [ENVIAR_MENU]", None, TENANT_ID, None,
        )
    assert "[ENVIAR_MENU]" not in text
    assert attachments == []


@pytest.mark.asyncio
async def test_attach_menu_with_cabecera_image():
    """When menu_cabecera_url is configured, header image comes first, then PDF."""
    text, attachments = await _attach_menu(
        "Aqui va [ENVIAR_MENU]",
        {
            "menu_pdf_url": "https://example.com/menu.pdf",
            "menu_cabecera_url": "https://example.com/header.jpg",
        },
        TENANT_ID,
        None,
    )
    assert "[ENVIAR_MENU]" not in text
    assert len(attachments) == 2
    # First: header image
    assert attachments[0]["type"] == "image"
    assert attachments[0]["url"] == "https://example.com/header.jpg"
    # Second: PDF document
    assert attachments[1]["type"] == "document"
    assert attachments[1]["url"] == "https://example.com/menu.pdf"


@pytest.mark.asyncio
async def test_attach_image_no_marker():
    text, attachment = await _attach_image("Sin imagen", TENANT_ID, None)
    assert text == "Sin imagen"
    assert attachment is None


@pytest.mark.asyncio
async def test_attach_image_with_match():
    with patch(
        "app.services.ai_orchestrator._find_product_image",
        new_callable=AsyncMock,
        return_value={
            "imagen_url": "https://storage.example.com/pizza.jpg",
            "nombre": "Hawaiana",
            "precio": 8900,
            "descripcion": "Jamón, piña y queso",
        },
    ):
        text, attachment = await _attach_image(
            "Mira nuestra [ENVIAR_IMAGEN:Hawaiana] pizza", TENANT_ID, None,
        )
    assert "[ENVIAR_IMAGEN" not in text
    assert attachment is not None
    assert attachment["type"] == "image"
    assert "Hawaiana" in attachment["file_name"]
    assert attachment["caption"].startswith("*Hawaiana*")
    assert "$8.900" in attachment["caption"]
    assert "Jamón, piña y queso" in attachment["caption"]


@pytest.mark.asyncio
async def test_attach_image_not_found():
    with patch(
        "app.services.ai_orchestrator._find_product_image",
        new_callable=AsyncMock,
        return_value=None,
    ):
        text, attachment = await _attach_image(
            "Mira [ENVIAR_IMAGEN:NoExiste]", TENANT_ID, None,
        )
    assert "[ENVIAR_IMAGEN" not in text
    assert attachment is None


@pytest.mark.asyncio
async def test_resolve_media_markers_full():
    """Test full resolve with menu + image + catchall."""
    with patch(
        "app.services.ai_orchestrator._auto_generate_menu_pdf",
        new_callable=AsyncMock,
        return_value="https://menu.pdf",
    ), patch(
        "app.services.ai_orchestrator._find_product_image",
        new_callable=AsyncMock,
        return_value={
            "imagen_url": "https://image.jpg",
            "nombre": "Pizza",
            "precio": 7500,
            "descripcion": "Deliciosa",
        },
    ):
        text, attachments = await _resolve_media_markers(
            "Menu: [ENVIAR_MENU] y foto [ENVIAR_IMAGEN:Pizza] [ENVIAR_ALGO]",
            None,
            TENANT_ID,
            None,
        )
    assert "[ENVIAR" not in text
    assert len(attachments) == 2


@pytest.mark.asyncio
async def test_resolve_media_markers_clean_text():
    """No markers → no attachments, text unchanged."""
    text, attachments = await _resolve_media_markers(
        "Solo texto sin marcadores", None, TENANT_ID, None,
    )
    assert text == "Solo texto sin marcadores"
    assert attachments == []


# ── Poll marker extraction ───────────────────────────────────────────

def test_extract_poll_basic():
    text, poll = _extract_poll(
        "Elige tu preferencia [ENVIAR_POLL:¿Qué salsa prefieres?|Soja|Agridulce|Ambas]"
    )
    assert "[ENVIAR_POLL" not in text
    assert poll is not None
    assert poll["type"] == "poll"
    assert poll["question"] == "¿Qué salsa prefieres?"
    assert poll["options"] == ["Soja", "Agridulce", "Ambas"]


def test_extract_poll_no_marker():
    text, poll = _extract_poll("Sin encuesta aquí")
    assert text == "Sin encuesta aquí"
    assert poll is None


def test_extract_poll_too_few_options():
    """Polls need at least question + 2 options = 3 parts."""
    text, poll = _extract_poll("[ENVIAR_POLL:¿Sí o no?|Sí]")
    assert poll is None


def test_extract_poll_many_options():
    options = "|".join([f"Opción {i}" for i in range(1, 8)])
    text, poll = _extract_poll(f"Vota: [ENVIAR_POLL:¿Cuál?|{options}]")
    assert poll is not None
    assert len(poll["options"]) == 7


# ── List marker extraction ───────────────────────────────────────────

def test_extract_list_basic():
    text, lst = _extract_list(
        "Nuestro menú [ENVIAR_LISTA:Combos|Ver opciones|Almuerzo:Combo 1,Combo 2|Cena:Combo 3,Combo 4]"
    )
    assert "[ENVIAR_LISTA" not in text
    assert lst is not None
    assert lst["type"] == "list"
    assert lst["title"] == "Combos"
    assert lst["button_text"] == "Ver opciones"
    assert len(lst["sections"]) == 2
    assert lst["sections"][0]["title"] == "Almuerzo"
    assert len(lst["sections"][0]["rows"]) == 2
    assert lst["sections"][0]["rows"][0]["title"] == "Combo 1"


def test_extract_list_no_marker():
    text, lst = _extract_list("Sin lista aquí")
    assert text == "Sin lista aquí"
    assert lst is None


def test_extract_list_too_few_parts():
    """Lists need title + button + at least 1 section = 3 parts."""
    text, lst = _extract_list("[ENVIAR_LISTA:Título|Botón]")
    assert lst is None


def test_extract_list_row_ids_generated():
    """Row IDs should be auto-generated from title."""
    _, lst = _extract_list("[ENVIAR_LISTA:Menu|Ver|Platos:Pizza Grande,Combo Familiar]")
    assert lst is not None
    rows = lst["sections"][0]["rows"]
    assert rows[0]["rowId"] == "pizza_grande"
    assert rows[1]["rowId"] == "combo_familiar"


# ── Resolve markers with polls and lists ─────────────────────────────

@pytest.mark.asyncio
async def test_resolve_media_markers_with_poll():
    text, attachments = await _resolve_media_markers(
        "¿Qué prefieres? [ENVIAR_POLL:¿Salsa?|Soja|Agridulce]",
        None, TENANT_ID, None,
    )
    assert "[ENVIAR" not in text
    polls = [a for a in attachments if a.get("type") == "poll"]
    assert len(polls) == 1
    assert polls[0]["question"] == "¿Salsa?"


@pytest.mark.asyncio
async def test_resolve_media_markers_with_list():
    text, attachments = await _resolve_media_markers(
        "Aquí nuestro menú [ENVIAR_LISTA:Menu|Ver|Platos:Pizza,Pasta]",
        None, TENANT_ID, None,
    )
    assert "[ENVIAR" not in text
    lists = [a for a in attachments if a.get("type") == "list"]
    assert len(lists) == 1
    assert lists[0]["title"] == "Menu"


@pytest.mark.asyncio
async def test_resolve_media_markers_mixed():
    """Test menu + poll in same response."""
    with patch(
        "app.services.ai_orchestrator._auto_generate_menu_pdf",
        new_callable=AsyncMock,
        return_value="https://menu.pdf",
    ):
        text, attachments = await _resolve_media_markers(
            "Menu [ENVIAR_MENU] y [ENVIAR_POLL:¿Bebida?|Agua|Jugo|Gaseosa]",
            None, TENANT_ID, None,
        )
    assert "[ENVIAR" not in text
    types = {a.get("type") for a in attachments}
    assert "document" in types
    assert "poll" in types


# ── Regression: _fetch_modifier_map query uses correct columns ───────

@pytest.mark.asyncio
async def test_fetch_modifier_map_query_does_not_reference_pmg_tenant_id():
    """Regression: producto_modifier_groups has no tenant_id column.

    The query must filter via modifier_groups.tenant_id, NOT pmg.tenant_id.
    If this test fails, the query is referencing a non-existent column and
    modifiers will silently fail to load.
    """
    import inspect
    source = inspect.getsource(_fetch_modifier_map)
    # Must NOT contain pmg.tenant_id (the old broken query)
    assert "pmg.tenant_id" not in source, (
        "BUG: _fetch_modifier_map references pmg.tenant_id but "
        "producto_modifier_groups has no tenant_id column. "
        "Use mg.tenant_id instead."
    )
    # Must contain mg.tenant_id (the correct filter)
    assert "mg.tenant_id" in source, (
        "BUG: _fetch_modifier_map does not filter by mg.tenant_id. "
        "Modifiers will load across tenants."
    )


@pytest.mark.asyncio
async def test_fetch_modifier_map_returns_empty_on_missing_tables():
    """If modifier tables don't exist, should return empty dict (not crash)."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("relation does not exist")
    result = await _fetch_modifier_map(mock_session, TENANT_ID)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_modifier_map_logs_error_on_failure():
    """Should log at ERROR level (not just debug) when query fails."""
    import logging
    target_logger = logging.getLogger("app.services.ai_orchestrator")
    handler = logging.handlers.MemoryHandler(capacity=100)
    handler.setLevel(logging.ERROR)
    target_logger.addHandler(handler)
    try:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("column X does not exist")
        await _fetch_modifier_map(mock_session, TENANT_ID)
        handler.flush()
        messages = [r.getMessage() for r in handler.buffer]
        assert any("Failed to load modifiers" in m for m in messages)
    finally:
        target_logger.removeHandler(handler)


# ── Regression: mesa token extraction ────────────────────────────────

def test_extract_mesa_token_present():
    msg, token = _extract_mesa_token("Hola! Quiero el menu [mesa:abc123def456abc123def456abc123de]")
    assert token == "abc123def456abc123def456abc123de"
    assert "[mesa:" not in msg

def test_extract_mesa_token_absent():
    msg, token = _extract_mesa_token("Hola quiero pedir")
    assert token is None
    assert msg == "Hola quiero pedir"


# ── Regression: order JSON extraction includes delivery fields ───────

def test_extract_order_json_with_delivery():
    text = '''Resumen:
```json
{
  "pedido_confirmado": true,
  "tipo_entrega": "DELIVERY",
  "direccion_entrega": "Av. O'Higgins 1234",
  "metodo_pago": "CONTRA_ENTREGA",
  "pago_confirmado": false,
  "items": [{"producto_id": "abc", "cantidad": 1}]
}
```'''
    data = extract_order_json(text)
    assert data is not None
    assert data["tipo_entrega"] == "DELIVERY"
    assert data["direccion_entrega"] == "Av. O'Higgins 1234"
    assert data["metodo_pago"] == "CONTRA_ENTREGA"


def test_extract_order_json_no_block():
    assert extract_order_json("Solo texto normal") is None


# ── Schema check: sucursal model uses grupo_repartidores_jid ─────────

def test_sucursal_model_uses_jid_not_phone():
    """Regression: column was renamed from grupo_repartidores_phone to _jid."""
    from shared.models.sucursal import Sucursal
    columns = {c.name for c in Sucursal.__table__.columns}
    assert "grupo_repartidores_jid" in columns, (
        "Sucursal model must have grupo_repartidores_jid (not phone)"
    )
    assert "grupo_repartidores_phone" not in columns, (
        "Stale column: grupo_repartidores_phone was renamed to _jid"
    )
