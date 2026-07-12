"""Tests for the admin copilot agent engine."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import SudamericaChatResponse
from app.services.agent_engine import run_agent


@pytest.fixture
def llm_text_response():
    """LLM response with just text (no tool calls)."""
    return {
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "Las ventas de hoy van muy bien, llevas $150.000 en 12 ordenes.",
            },
        }],
        "usage": {"total_tokens": 250},
    }


@pytest.fixture
def llm_tool_call_response():
    """LLM response requesting a tool call."""
    return {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "consultar_metricas",
                        "arguments": "{}",
                    },
                }],
            },
        }],
        "usage": {"total_tokens": 100},
    }


@pytest.fixture
def llm_final_response():
    """LLM response after receiving tool results."""
    return {
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "Segun las metricas, tus ingresos totales son $500.000.",
            },
        }],
        "usage": {"total_tokens": 150},
    }


@pytest.mark.asyncio
async def test_run_agent_simple_response(settings, mock_http_client, llm_text_response):
    """Agent returns directly when LLM doesn't call any tools."""
    mock_response = AsyncMock()
    mock_response.json.return_value = llm_text_response
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response

    result = await run_agent(
        system_prompt="Eres Sudamérica AI",
        message="Hola, como van las ventas?",
        history=[],
        tenant_id="00000000-0000-0000-0000-000000000001",
        settings=settings,
        http_client=mock_http_client,
    )

    assert isinstance(result, SudamericaChatResponse)
    assert "ventas" in result.response.lower()
    assert result.tokens_used == 250
    assert len(result.tools_used) == 0


@pytest.mark.asyncio
async def test_run_agent_with_tool_call(
    settings, mock_http_client,
    llm_tool_call_response, llm_final_response,
):
    """Agent executes tool call and returns final response."""
    # First call: LLM requests tool call
    # Second call: LLM gives final response after tool result
    mock_resp_1 = AsyncMock()
    mock_resp_1.json.return_value = llm_tool_call_response
    mock_resp_1.raise_for_status = MagicMock()

    mock_resp_2 = AsyncMock()
    mock_resp_2.json.return_value = llm_final_response
    mock_resp_2.raise_for_status = MagicMock()

    mock_http_client.post.side_effect = [mock_resp_1, mock_resp_2]

    # Mock the tool execution (api_execute call)
    mock_tool_get = AsyncMock()
    mock_tool_get.json.return_value = {"total_revenue": 500000, "total_ventas": 45}
    mock_tool_get.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_tool_get

    result = await run_agent(
        system_prompt="Eres Sudamérica AI",
        message="Dame las metricas del restaurante",
        history=[],
        tenant_id="00000000-0000-0000-0000-000000000001",
        settings=settings,
        http_client=mock_http_client,
    )

    assert isinstance(result, SudamericaChatResponse)
    assert "metricas" in result.response.lower() or "ingresos" in result.response.lower()
    assert result.tokens_used == 250  # 100 + 150
    assert len(result.tools_used) >= 1
    assert result.tools_used[0].name == "consultar_metricas"


@pytest.mark.asyncio
async def test_run_agent_max_iterations(settings, mock_http_client, llm_tool_call_response):
    """Agent stops after MAX_TOOL_CALLS iterations."""
    settings.MAX_TOOL_CALLS = 2

    mock_resp = AsyncMock()
    mock_resp.json.return_value = llm_tool_call_response
    mock_resp.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_resp

    mock_tool_get = AsyncMock()
    mock_tool_get.json.return_value = {"data": []}
    mock_tool_get.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_tool_get

    result = await run_agent(
        system_prompt="Eres Sudamérica AI",
        message="Dame todo",
        history=[],
        tenant_id="00000000-0000-0000-0000-000000000001",
        settings=settings,
        http_client=mock_http_client,
    )

    assert "limite" in result.response.lower()
    # Regression: the MAX_TOOL_CALLS path used to reference an undefined
    # `total_tokens` (NameError). It must now sum the per-call token counts.
    assert result.tokens_used == 200  # 2 iterations x 100 tokens


@pytest.mark.asyncio
async def test_generate_response_no_tools(settings, mock_http_client, llm_text_response):
    """generate_response makes exactly ONE LLM call and NEVER offers tools."""
    from app.schemas.chat import GenerateResponse
    from app.services.agent_engine import generate_response

    mock_response = AsyncMock()
    mock_response.json.return_value = llm_text_response
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response

    result = await generate_response(
        system_prompt="Eres el asistente de Sudamérica AI",
        message="Hola, quiero hacer un pedido",
        history=[
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "buenas"},
        ],
        settings=settings,
        http_client=mock_http_client,
    )

    assert isinstance(result, GenerateResponse)
    assert result.response
    assert result.tokens_used == 250
    assert result.model_used
    # Exactly one LLM call and NO tools were ever sent in the payload.
    assert mock_http_client.post.call_count == 1
    sent_payload = mock_http_client.post.call_args.kwargs["json"]
    assert "tools" not in sent_payload
