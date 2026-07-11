"""Tests for interactive WhatsApp features: polls, lists, presence, debounce, audio STT."""

import asyncio
import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.whatsapp_service import (
    _button_response_text,
    _debounce_buffers,
    _debounce_key,
    _enqueue_debounce,
    _flush_debounce_buffer,
    _list_response_text,
    _list_to_numbered_text,
    _normalize_phone,
    _send_interactive_extras,
    send_list,
    send_message,
    send_poll,
    send_presence,
)
from .conftest import TEST_SETTINGS, TENANT_ID


# ── Send Presence ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_presence_composing():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()

    async def mock_post(self, path, **kwargs):
        assert "/chat/sendPresence/" in path
        payload = kwargs.get("json", {})
        assert payload["presence"] == "composing"
        assert payload["number"] == "56912345678"
        return mock_resp

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        await send_presence("56912345678", "instance-1", TEST_SETTINGS)


@pytest.mark.asyncio
async def test_send_presence_recording():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()

    async def mock_post(self, path, **kwargs):
        assert kwargs["json"]["presence"] == "recording"
        return mock_resp

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        await send_presence("56912345678", "instance-1", TEST_SETTINGS, presence="recording")


@pytest.mark.asyncio
async def test_send_presence_failure_does_not_raise():
    """Presence failures should be logged, not raised."""
    import httpx

    async def mock_post(self, path, **kwargs):
        raise httpx.HTTPError("Connection refused")

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        # Should not raise
        await send_presence("56912345678", "instance-1", TEST_SETTINGS)


# ── Send Poll ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_poll_basic():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"key": {"id": "poll-123"}}
    captured = {}

    async def mock_post(self, path, **kwargs):
        captured["path"] = path
        captured["payload"] = kwargs.get("json", {})
        return mock_resp

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        result = await send_poll(
            "56912345678",
            "¿Prefieres salsa de soja o agridulce?",
            ["Salsa de soja", "Salsa agridulce", "Ambas"],
            "instance-1",
            TEST_SETTINGS,
        )

    assert "/message/sendPoll/instance-1" in captured["path"]
    assert captured["payload"]["name"] == "¿Prefieres salsa de soja o agridulce?"
    assert captured["payload"]["values"] == ["Salsa de soja", "Salsa agridulce", "Ambas"]
    assert captured["payload"]["selectableCount"] == 1
    assert result["key"]["id"] == "poll-123"


@pytest.mark.asyncio
async def test_send_poll_multi_select():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"key": {"id": "poll-456"}}
    captured = {}

    async def mock_post(self, path, **kwargs):
        captured["payload"] = kwargs.get("json", {})
        return mock_resp

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        await send_poll(
            "56912345678", "¿Qué salsas?",
            ["Ketchup", "Mostaza", "Mayonesa"],
            "instance-1", TEST_SETTINGS,
            selectable_count=3,
        )

    assert captured["payload"]["selectableCount"] == 3


# ── Send List ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_list_basic():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"key": {"id": "list-123"}}
    captured = {}

    sections = [
        {
            "title": "Combos Almuerzo",
            "rows": [
                {"title": "Combo 1", "description": "$5.990", "rowId": "combo_1"},
                {"title": "Combo 2", "description": "$7.990", "rowId": "combo_2"},
            ],
        },
    ]

    async def mock_post(self, path, **kwargs):
        captured["path"] = path
        captured["payload"] = kwargs.get("json", {})
        return mock_resp

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        result = await send_list(
            "56912345678", "Nuestros Combos", "Elige tu favorito",
            "Ver opciones", sections, "instance-1", TEST_SETTINGS,
        )

    assert "/message/sendList/instance-1" in captured["path"]
    assert captured["payload"]["title"] == "Nuestros Combos"
    assert captured["payload"]["buttonText"] == "Ver opciones"
    assert len(captured["payload"]["sections"]) == 1
    assert result["key"]["id"] == "list-123"


# ── Numbered-options text menu (replaces interactive lists) ───────────

def test_list_to_numbered_text_single_section():
    list_data = {
        "title": "Nuestros Combos",
        "sections": [
            {"rows": [
                {"title": "Combo 1", "description": "$5.990"},
                {"title": "Combo 2", "description": "$7.990"},
            ]},
        ],
    }
    assert _list_to_numbered_text(list_data) == (
        "*Nuestros Combos*\n\n1) Combo 1 — $5.990\n2) Combo 2 — $7.990"
    )


def test_list_to_numbered_text_numbers_continuously_across_sections():
    list_data = {
        "title": "Menú",
        "sections": [
            {"title": "Entradas", "rows": [{"title": "Empanada"}]},
            {"title": "Fondos", "rows": [{"title": "Lomo"}, {"title": "Pollo"}]},
        ],
    }
    text = _list_to_numbered_text(list_data)
    assert "_Entradas_\n1) Empanada" in text
    assert "_Fondos_\n2) Lomo\n3) Pollo" in text


@pytest.mark.asyncio
async def test_send_interactive_extras_sends_numbered_text_not_list():
    captured = []
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {}

    async def mock_post(self, path, **kwargs):
        captured.append((path, kwargs.get("json", {})))
        return mock_resp

    ai_result = {
        "list_message": {
            "title": "Nuestros Combos",
            "button_text": "Ver opciones",
            "sections": [
                {"title": "Almuerzo", "rows": [
                    {"title": "Combo 1", "description": "$5.990", "rowId": "c1"},
                    {"title": "Combo 2", "description": "$7.990", "rowId": "c2"},
                ]},
            ],
        }
    }

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post), \
         patch("app.services.whatsapp_service.send_presence", new=AsyncMock()), \
         patch("app.services.whatsapp_service.asyncio.sleep", new=AsyncMock()):
        await _send_interactive_extras(
            ai_result, "56912345678", "instance-1", TEST_SETTINGS,
        )

    paths = [p for p, _ in captured]
    # The interactive list endpoint must NOT be hit anymore…
    assert not any("/message/sendList/" in p for p in paths)
    # …instead a single text message with numbered options is sent.
    text_calls = [body for p, body in captured if "/message/sendText/" in p]
    assert len(text_calls) == 1
    sent_text = text_calls[0]["text"]
    assert "1) Combo 1" in sent_text
    assert "2) Combo 2" in sent_text


# ── Debounce ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_debounce_key_format():
    key = _debounce_key(TENANT_ID, "56912345678")
    assert key == (str(TENANT_ID), "56912345678")


@pytest.mark.asyncio
async def test_enqueue_debounce_first_message():
    """First message should create a buffer entry."""
    _debounce_buffers.clear()
    session_factory = AsyncMock()

    data = {"instance_name": "inst-1", "sender": "56912345678", "message": "Hola"}

    buffered = await _enqueue_debounce(
        data, "Hola", TENANT_ID, "56912345678",
        4.0, TEST_SETTINGS, session_factory,
    )
    assert buffered is True
    key = _debounce_key(TENANT_ID, "56912345678")
    assert key in _debounce_buffers
    assert _debounce_buffers[key]["messages"] == ["Hola"]

    # Clean up timer
    entry = _debounce_buffers.pop(key, None)
    if entry and entry.get("timer_task"):
        entry["timer_task"].cancel()


@pytest.mark.asyncio
async def test_enqueue_debounce_second_message_appends():
    """Second message from same sender should append to buffer."""
    _debounce_buffers.clear()
    session_factory = AsyncMock()

    data = {"instance_name": "inst-1", "sender": "56912345678", "message": "Hola"}

    await _enqueue_debounce(
        data, "Hola", TENANT_ID, "56912345678",
        4.0, TEST_SETTINGS, session_factory,
    )
    await _enqueue_debounce(
        data, "quiero pedir", TENANT_ID, "56912345678",
        4.0, TEST_SETTINGS, session_factory,
    )

    key = _debounce_key(TENANT_ID, "56912345678")
    assert len(_debounce_buffers[key]["messages"]) == 2
    assert _debounce_buffers[key]["messages"] == ["Hola", "quiero pedir"]

    # Clean up
    entry = _debounce_buffers.pop(key, None)
    if entry and entry.get("timer_task"):
        entry["timer_task"].cancel()


@pytest.mark.asyncio
async def test_debounce_different_tenants_isolated():
    """Different tenants should have separate buffers."""
    _debounce_buffers.clear()
    session_factory = AsyncMock()
    tenant2 = uuid.UUID("00000000-0000-0000-0000-000000000099")

    data1 = {"instance_name": "inst-1", "sender": "56912345678", "message": "Hola"}
    data2 = {"instance_name": "inst-2", "sender": "56912345678", "message": "Hello"}

    await _enqueue_debounce(data1, "Hola", TENANT_ID, "56912345678", 4.0, TEST_SETTINGS, session_factory)
    await _enqueue_debounce(data2, "Hello", tenant2, "56912345678", 4.0, TEST_SETTINGS, session_factory)

    key1 = _debounce_key(TENANT_ID, "56912345678")
    key2 = _debounce_key(tenant2, "56912345678")
    assert key1 in _debounce_buffers
    assert key2 in _debounce_buffers
    assert _debounce_buffers[key1]["messages"] == ["Hola"]
    assert _debounce_buffers[key2]["messages"] == ["Hello"]

    # Clean up
    for k in [key1, key2]:
        entry = _debounce_buffers.pop(k, None)
        if entry and entry.get("timer_task"):
            entry["timer_task"].cancel()


@pytest.mark.asyncio
async def test_flush_debounce_merges_messages():
    """Flush should merge buffered messages with newlines."""
    from contextlib import asynccontextmanager

    _debounce_buffers.clear()

    key = _debounce_key(TENANT_ID, "56912345678")

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    @asynccontextmanager
    async def mock_session_ctx():
        yield mock_db

    def session_factory():
        return mock_session_ctx()

    first_data = {
        "instance_name": "inst-1",
        "sender": "56912345678",
        "message": "original",
    }

    _debounce_buffers[key] = {
        "messages": ["Hola", "quiero pedir", "una pizza grande"],
        "first_data": dict(first_data),
        "session_factory": session_factory,
    }

    with (
        patch("app.services.whatsapp_service.process_incoming", new_callable=AsyncMock) as mock_process,
        patch("shared.database.session.set_instance_lookup_context", new_callable=AsyncMock),
    ):
        await _flush_debounce_buffer(key, TEST_SETTINGS)

        assert mock_process.called
        call_args = mock_process.call_args
        merged = call_args[0][0]["message"]
        assert merged == "Hola\nquiero pedir\nuna pizza grande"
        # _skip_debounce should be True to avoid re-buffering
        assert call_args[1].get("_skip_debounce") is True

    assert key not in _debounce_buffers


# ── Audio STT ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transcribe_audio_calls_stt_endpoint():
    from app.services.whatsapp_service import _transcribe_audio

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"transcription": "Hola quiero una pizza"}

    async def mock_post(self, path, **kwargs):
        assert "/stt/transcribe" in path
        payload = kwargs.get("json", {})
        assert "audio_base64" in payload
        assert payload["mimetype"] == "audio/ogg"
        assert payload["language"] == "es"
        return mock_resp

    headers = {
        "ai_config": {"Authorization": "Bearer x"},
    }

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        result = await _transcribe_audio(
            b"fake-audio-bytes", "audio/ogg", TENANT_ID, TEST_SETTINGS, headers,
        )

    assert result == "Hola quiero una pizza"


@pytest.mark.asyncio
async def test_transcribe_audio_failure_returns_none():
    from app.services.whatsapp_service import _transcribe_audio
    import httpx

    async def mock_post(self, path, **kwargs):
        raise httpx.HTTPError("STT service down")

    headers = {"ai_config": {"Authorization": "Bearer x"}}

    with patch("app.services.whatsapp_service.HttpClient.post", mock_post):
        result = await _transcribe_audio(
            b"fake-audio-bytes", "audio/ogg", TENANT_ID, TEST_SETTINGS, headers,
        )

    assert result is None


# ── Interactive Response Parsing ─────────────────────────────────────


def test_list_response_text_extracts_title():
    """Extract selected option title from WhatsApp list response."""
    message = {
        "listResponseMessage": {
            "title": "Hacer un pedido",
            "listType": 1,
            "singleSelectReply": {"selectedRowId": "hacer_un_pedido"},
        }
    }
    assert _list_response_text(message) == "Hacer un pedido"


def test_list_response_text_falls_back_to_row_id():
    """If title is empty, fall back to selectedRowId."""
    message = {
        "listResponseMessage": {
            "title": "",
            "singleSelectReply": {"selectedRowId": "ver_el_menu"},
        }
    }
    assert _list_response_text(message) == "ver el menu"


def test_list_response_text_returns_empty_for_non_list():
    """Non-list messages return empty string."""
    message = {"conversation": "hello"}
    assert _list_response_text(message) == ""


def test_list_response_text_returns_empty_for_empty_dict():
    assert _list_response_text({}) == ""


def test_button_response_text_extracts_display_text():
    """Extract selected button display text."""
    message = {
        "buttonsResponseMessage": {
            "selectedDisplayText": "Delivery",
            "selectedButtonId": "btn_delivery",
        }
    }
    assert _button_response_text(message) == "Delivery"


def test_button_response_text_falls_back_to_button_id():
    """If display text is empty, fall back to button ID."""
    message = {
        "buttonsResponseMessage": {
            "selectedDisplayText": "",
            "selectedButtonId": "btn_retiro",
        }
    }
    assert _button_response_text(message) == "btn_retiro"


def test_button_response_text_returns_empty_for_non_button():
    message = {"conversation": "hello"}
    assert _button_response_text(message) == ""


def test_extract_text_prefers_list_response_over_caption():
    """_extract_text should find list response before trying captions."""
    from app.services.whatsapp_service import _extract_text

    message = {
        "listResponseMessage": {
            "title": "Reservar mesa",
            "singleSelectReply": {"selectedRowId": "reservar_mesa"},
        }
    }
    assert _extract_text(message) == "Reservar mesa"


# ── Poll Vote Extraction (in whatsapp.py routes) ────────────────────


def test_poll_vote_extraction():
    """Poll votes should be extracted from data.pollUpdates."""
    from app.routes.whatsapp import _extract_text_and_media

    data = {
        "message": {
            "pollUpdateMessage": {
                "pollCreationMessageKey": {"id": "poll-abc"},
            }
        },
        "pollUpdates": [
            {"vote": ["Transferencia"]}
        ],
    }
    text, media = _extract_text_and_media(data)
    assert text == "Transferencia"
    assert media is None


def test_poll_multi_vote_extraction():
    """Multiple poll votes should be comma-separated."""
    from app.routes.whatsapp import _extract_text_and_media

    data = {
        "message": {},
        "pollUpdates": [
            {"vote": ["Salsa de soja", "Ambas"]}
        ],
    }
    text, media = _extract_text_and_media(data)
    assert text == "Salsa de soja, Ambas"


def test_poll_empty_votes_falls_through():
    """Empty vote array should fall through to normal text extraction."""
    from app.routes.whatsapp import _extract_text_and_media

    data = {
        "message": {"conversation": "hello"},
        "pollUpdates": [{"vote": []}],
    }
    text, media = _extract_text_and_media(data)
    assert text == "hello"


def test_no_poll_updates_uses_normal_text():
    """Without pollUpdates, normal text extraction should work."""
    from app.routes.whatsapp import _extract_text_and_media

    data = {"message": {"conversation": "quiero una pizza"}}
    text, media = _extract_text_and_media(data)
    assert text == "quiero una pizza"


# ── Group Message Handling ───────────────────────────────────────────


def test_extract_sender_allows_group_messages():
    """Group messages (@g.us) should NOT be blocked; they should be tagged."""
    from app.routes.whatsapp import _extract_sender

    payload = {
        "data": {
            "key": {
                "remoteJid": "120363040123456789@g.us",
                "fromMe": False,
                "participant": "56912345678@s.whatsapp.net",
            },
            "message": {"conversation": "tomo"},
        }
    }
    result = _extract_sender(payload)
    assert result is not None
    data, key, sender = result
    assert sender == "120363040123456789@g.us"
    assert data["_is_group"] is True
    assert data["_group_jid"] == "120363040123456789@g.us"
    assert data["_participant_jid"] == "56912345678@s.whatsapp.net"


def test_extract_sender_blocks_broadcast():
    """Broadcast messages should still be blocked."""
    from app.routes.whatsapp import _extract_sender

    payload = {
        "data": {
            "key": {"remoteJid": "status@broadcast", "fromMe": False},
        }
    }
    assert _extract_sender(payload) is None


def test_extract_sender_blocks_group_without_participant():
    """Group messages without participant field should be blocked."""
    from app.routes.whatsapp import _extract_sender

    payload = {
        "data": {
            "key": {
                "remoteJid": "120363040123456789@g.us",
                "fromMe": False,
            },
        }
    }
    assert _extract_sender(payload) is None


def test_extract_sender_normal_message_unchanged():
    """Normal 1:1 messages should work as before."""
    from app.routes.whatsapp import _extract_sender

    payload = {
        "data": {
            "key": {"remoteJid": "56912345678@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "hello"},
        }
    }
    result = _extract_sender(payload)
    assert result is not None
    data, key, sender = result
    assert sender == "56912345678@s.whatsapp.net"
    assert "_is_group" not in data
