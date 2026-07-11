"""Tests for onboarding chat helpers and route."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.routes.onboarding import (
    _build_llm_messages,
    _parse_ai_response,
)


# ── _parse_ai_response ──────────────────────────────────────────────

def test_parse_ai_response_basic():
    data = {
        "content": json.dumps({
            "reply": "Hola! Como se llama tu restaurante?",
            "extractedData": {},
            "complete": False,
        }),
        "tokens_used": 42,
    }
    result = _parse_ai_response(data)
    assert result.reply == "Hola! Como se llama tu restaurante?"
    assert result.extractedData == {}
    assert result.complete is False


def test_parse_ai_response_with_extracted_data():
    data = {
        "content": json.dumps({
            "reply": "Genial! Y que tipo de comida venden?",
            "extractedData": {"tenant_nombre": "La Tarantella", "tipo_comida": "pizzas"},
            "complete": False,
        }),
        "tokens_used": 55,
    }
    result = _parse_ai_response(data)
    assert result.extractedData == {"tenant_nombre": "La Tarantella", "tipo_comida": "pizzas"}


def test_parse_ai_response_filters_placeholders():
    data = {
        "content": json.dumps({
            "reply": "Ok",
            "extractedData": {"tono": "formal|casual|mixto", "nombre": "Juan", "email": "..."},
            "complete": False,
        }),
        "tokens_used": 10,
    }
    result = _parse_ai_response(data)
    assert result.extractedData == {"nombre": "Juan"}


def test_parse_ai_response_complete():
    data = {
        "content": json.dumps({
            "reply": "Perfecto! Todo listo!",
            "extractedData": {},
            "complete": True,
        }),
        "tokens_used": 20,
    }
    result = _parse_ai_response(data)
    assert result.complete is True


def test_parse_ai_response_missing_fields():
    data = {"content": json.dumps({}), "tokens_used": 0}
    result = _parse_ai_response(data)
    assert result.reply == "No entendi bien, podrias repetirlo?"
    assert result.extractedData == {}
    assert result.complete is False


def test_parse_ai_response_input_type_password():
    data = {
        "content": json.dumps({
            "reply": "Ahora elige una contrasena segura",
            "extractedData": {},
            "complete": False,
            "inputType": "password",
        }),
        "tokens_used": 15,
    }
    result = _parse_ai_response(data)
    assert result.inputType == "password"


def test_parse_ai_response_input_type_defaults_to_text():
    data = {
        "content": json.dumps({
            "reply": "Hola!",
            "extractedData": {},
            "complete": False,
        }),
        "tokens_used": 10,
    }
    result = _parse_ai_response(data)
    assert result.inputType == "text"


def test_parse_ai_response_input_type_invalid_falls_back():
    data = {
        "content": json.dumps({
            "reply": "test",
            "extractedData": {},
            "complete": False,
            "inputType": "invalid",
        }),
        "tokens_used": 10,
    }
    result = _parse_ai_response(data)
    assert result.inputType == "text"


def test_parse_ai_response_filters_empty_strings():
    data = {
        "content": json.dumps({
            "reply": "test",
            "extractedData": {"nombre": "", "email": "  ", "telefono": "123456"},
            "complete": False,
        }),
        "tokens_used": 10,
    }
    result = _parse_ai_response(data)
    assert result.extractedData == {"telefono": "123456"}


# ── _build_llm_messages ─────────────────────────────────────────────

def test_build_llm_messages_basic():
    system = "Eres Sudamérica AI"
    history = [
        {"role": "user", "text": "Hola"},
        {"role": "bot", "text": "Bienvenido!"},
    ]
    messages = _build_llm_messages(system, history)
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "Eres Sudamérica AI"}
    assert messages[1] == {"role": "user", "content": "Hola"}
    assert messages[2] == {"role": "assistant", "content": "Bienvenido!"}


def test_build_llm_messages_empty_history():
    messages = _build_llm_messages("system prompt", [])
    assert len(messages) == 1
    assert messages[0]["role"] == "system"


def test_build_llm_messages_missing_text():
    history = [{"role": "user"}]
    messages = _build_llm_messages("sys", history)
    assert messages[1]["content"] == ""


# ── onboarding_chat route ────────────────────────────────────────────

async def test_onboarding_chat_success(client):
    """POST /onboarding/chat with mocked AI_dialer."""
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "content": json.dumps({
            "reply": "Hola! Soy Sudamérica AI",
            "extractedData": {},
            "complete": False,
        }),
        "tokens_used": 30,
    }

    with patch("app.routes.onboarding.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        body = {
            "messages": [{"role": "user", "text": "Hola"}],
            "currentData": {},
        }
        resp = await client.post("/api/v1/core/onboarding/chat", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["reply"] == "Hola! Soy Sudamérica AI"


async def test_onboarding_chat_ai_down(client):
    """When AI_dialer is unreachable, return fallback reply."""
    import httpx as httpx_mod

    with patch("app.routes.onboarding.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx_mod.ConnectError("Connection refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        body = {"messages": [{"role": "user", "text": "Hola"}], "currentData": {}}
        resp = await client.post("/api/v1/core/onboarding/chat", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert "problemas tecnicos" in data["reply"]
