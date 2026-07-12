"""Agent engine — LLM tool-calling loop for the admin copilot.

Receives a system prompt (from api_execute) and a user message,
runs the LLM with admin tools, executes tool calls, and returns
the final response.

Supports vision: when a file (image) is attached, it is sent as
multimodal content to the LLM for analysis.
"""

import base64
import csv
import io
import json
import logging

import httpx

from app.config import OpenAgentSettings
from app.schemas.chat import (
    FileAttachment,
    GenerateResponse,
    SudamericaChatResponse,
    ToolUsage,
)
from app.services.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

# Image MIME types that can be sent directly to the LLM vision API
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# Tabular file types that we parse into text
_TABULAR_TYPES = {"text/csv", "application/vnd.ms-excel",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def _parse_csv_to_text(raw_bytes: bytes) -> str:
    """Parse CSV bytes into a readable text table."""
    text = raw_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return "(CSV vacio)"
    # Format as markdown-ish table
    lines = []
    for i, row in enumerate(rows[:200]):  # cap at 200 rows
        lines.append(" | ".join(row))
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    if len(rows) > 200:
        lines.append(f"... ({len(rows) - 200} filas mas)")
    return "\n".join(lines)


def _build_image_content(message: str, file: FileAttachment) -> list:
    """Build multimodal content for image files."""
    return [
        {"type": "text", "text": message},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{file.content_type};base64,{file.data_base64}",
            },
        },
    ]


def _build_pdf_content(message: str, file: FileAttachment, raw_bytes: bytes) -> list | str:
    """Extract text from PDF or fall back to multimodal image content."""
    try:
        text_content = raw_bytes.decode("utf-8", errors="replace")
        clean = "".join(c for c in text_content if c.isprintable() or c in "\n\r\t")
        if len(clean) < 50:
            return [
                {"type": "text", "text": f"{message}\n\n(Archivo PDF adjunto: {file.filename})"},
                {"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{file.data_base64}"}},
            ]
        return f"{message}\n\n--- Contenido del PDF {file.filename} ---\n{clean[:10000]}"
    except Exception:
        return f"{message}\n\n(No se pudo leer el PDF {file.filename})"


def _build_user_content(message: str, file: FileAttachment | None) -> list | str:
    """Build the user message content, optionally with image or file data."""
    if file is None:
        return message

    raw_bytes = base64.b64decode(file.data_base64)

    if file.content_type in _IMAGE_TYPES:
        return _build_image_content(message, file)
    if file.content_type in _TABULAR_TYPES:
        table_text = _parse_csv_to_text(raw_bytes)
        return f"{message}\n\n--- Contenido del archivo {file.filename} ---\n{table_text}"
    if file.content_type == "application/pdf":
        return _build_pdf_content(message, file, raw_bytes)
    return f"{message}\n\n(Archivo adjunto: {file.filename}, tipo: {file.content_type})"


async def _call_llm(
    messages: list[dict],
    config: dict,
    settings: OpenAgentSettings,
    http_client: httpx.AsyncClient,
    tools: list[dict] | None = None,
) -> dict:
    """Call the LLM via OpenAI-compatible API with optional tools."""
    payload: dict = {
        "model": config["model"],
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    url = f"{config['base_url']}/chat/completions"

    response = await http_client.post(url, json=payload, headers=headers, timeout=90.0)
    response.raise_for_status()
    return response.json()


async def _execute_tool_calls(
    tool_calls: list[dict],
    messages: list[dict],
    tools_used: list,
    tenant_uuid,
    tenant_id: str,
    settings,
    http_client,
) -> None:
    """Execute all tool calls from an LLM response and append results to messages."""
    for tc in tool_calls:
        func = tc.get("function", {})
        tool_name = func.get("name", "")
        try:
            arguments = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}

        logger.info("Executing tool: %s(%s) for tenant %s", tool_name, arguments, tenant_id)
        tool_result = await execute_tool(tool_name, arguments, tenant_uuid, settings, http_client)

        tools_used.append(ToolUsage(name=tool_name, result_summary=tool_result[:200]))
        messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": tool_result})


async def run_agent(
    system_prompt: str,
    message: str,
    history: list[dict],
    tenant_id: str,
    settings: OpenAgentSettings,
    http_client: httpx.AsyncClient,
    file: FileAttachment | None = None,
) -> SudamericaChatResponse:
    """Run the full agent loop: LLM → tools → LLM → ... → final response."""
    from uuid import UUID

    tenant_uuid = UUID(tenant_id)
    config = settings.provider_config

    # Build initial message list
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)

    # Build user content (text or multimodal with image)
    user_content = _build_user_content(message, file)
    messages.append({"role": "user", "content": user_content})

    token_counts: list[int] = []
    tools_used: list[ToolUsage] = []
    iterations = 0

    while iterations < settings.MAX_TOOL_CALLS:
        iterations = iterations + 1

        result = await _call_llm(
            messages, config, settings, http_client,
            tools=TOOL_DEFINITIONS,
        )

        choice = result.get("choices", [{}])[0]
        usage = result.get("usage", {})
        token_counts.append(usage.get("total_tokens", 0))
        finish_reason = choice.get("finish_reason", "stop")
        assistant_message = choice.get("message", {})

        # If LLM wants to call tools
        tool_calls = assistant_message.get("tool_calls")
        if finish_reason == "tool_calls" or tool_calls:
            messages.append(assistant_message)
            await _execute_tool_calls(
                tool_calls or [], messages, tools_used,
                tenant_uuid, tenant_id, settings, http_client,
            )
            continue

        # Final response (no more tool calls)
        response_text = assistant_message.get("content", "")
        return SudamericaChatResponse(
            response=response_text,
            tokens_used=sum(token_counts),
            model_used=config["model"],
            tools_used=tools_used,
        )

    # Safety: max iterations reached
    logger.warning("Max tool call iterations (%d) reached for tenant %s", settings.MAX_TOOL_CALLS, tenant_id)
    return SudamericaChatResponse(
        response="He alcanzado el limite de consultas para esta respuesta. Por favor reformula tu pregunta.",
        tokens_used=sum(token_counts),
        model_used=config["model"],
        tools_used=tools_used,
    )


async def generate_response(
    system_prompt: str,
    message: str,
    history: list[dict],
    settings: OpenAgentSettings,
    http_client: httpx.AsyncClient,
    file: FileAttachment | None = None,
) -> GenerateResponse:
    """Single LLM call WITHOUT tools — for the customer chat and onboarding.

    Unlike run_agent, this NEVER exposes the admin TOOL_DEFINITIONS: it makes
    exactly one _call_llm with tools=None and returns the generated text.
    api_execute owns the prompt, history and persistence; open_agent only
    generates text here. Reuses _build_user_content for vision/file support.
    """
    config = settings.provider_config

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)

    user_content = _build_user_content(message, file)
    messages.append({"role": "user", "content": user_content})

    result = await _call_llm(messages, config, settings, http_client, tools=None)

    choice = result.get("choices", [{}])[0]
    usage = result.get("usage", {})
    assistant_message = choice.get("message", {})
    response_text = assistant_message.get("content", "") or ""

    return GenerateResponse(
        response=response_text,
        tokens_used=usage.get("total_tokens", 0),
        model_used=config["model"],
    )
