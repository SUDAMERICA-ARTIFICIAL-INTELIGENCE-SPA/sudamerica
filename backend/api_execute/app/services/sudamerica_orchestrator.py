"""Sudamérica AI Orchestrator — builds admin context and forwards to open_agent.

api_execute owns: system prompt, conversation persistence, auth.
open_agent owns: LLM reasoning, tool execution.
"""

import logging
from uuid import UUID

import httpx
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ApiExecuteSettings
from app.prompts_ai import sudamerica_admin_prompt
from app.services.tenant_rubro import load_tenant_rubro as _load_tenant_rubro
from shared.database.session import set_tenant_context
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)


async def _load_tenant_name(session: AsyncSession, tenant_id: UUID) -> str:
    result = await session.execute(
        sql_text("SELECT nombre FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one_or_none() or "tu restaurante"


async def _load_sudamerica_history(
    session: AsyncSession,
    tenant_id: UUID,
    usuario_id: UUID,
    limit: int = 20,
) -> list[dict[str, str]]:
    """Load recent Sudamérica AI conversation history for this user."""
    result = await session.execute(
        sql_text(
            "SELECT role, content FROM ai_conversations "
            "WHERE tenant_id = :tid AND usuario_id = :uid AND canal = 'SUDAMERICA' "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"tid": str(tenant_id), "uid": str(usuario_id), "lim": limit},
    )
    rows = [{"role": r["role"], "content": r["content"]} for r in result.mappings().all()]
    rows.reverse()
    return rows


async def _save_message(
    session: AsyncSession,
    tenant_id: UUID,
    usuario_id: UUID,
    role: str,
    content: str,
    tokens: int | None,
    modelo: str | None,
) -> None:
    """Persist a sudamerica conversation message."""
    await session.execute(
        sql_text(
            "INSERT INTO ai_conversations "
            "(tenant_id, usuario_id, role, content, tokens_used, modelo, canal, status) "
            "VALUES (:tid, :uid, :role, :content, :tokens, :modelo, 'SUDAMERICA', 'SENT')"
        ),
        {
            "tid": str(tenant_id),
            "uid": str(usuario_id),
            "role": role,
            "content": content,
            "tokens": tokens,
            "modelo": modelo,
        },
    )


async def orchestrate_sudamerica_chat(
    session: AsyncSession,
    tenant_id: UUID,
    usuario_id: UUID,
    user_name: str,
    message: str,
    settings: ApiExecuteSettings,
    file_data: dict | None = None,
) -> dict:
    """Orchestrate Sudamérica AI chat: build prompt, forward to open_agent, persist.

    Flow:
    1. Build system prompt with tenant context
    2. Load conversation history
    3. Save user message
    4. Forward to open_agent
    5. Save assistant response
    6. Return response
    """
    tenant_name = await _load_tenant_name(session, tenant_id)
    rubro = await _load_tenant_rubro(session, tenant_id)
    system_prompt = sudamerica_admin_prompt(tenant_name, user_name, rubro=rubro)
    history = await _load_sudamerica_history(session, tenant_id, usuario_id)

    # Set RLS context before writing
    await set_tenant_context(session, str(tenant_id))

    # Save user message
    await _save_message(session, tenant_id, usuario_id, "user", message, None, None)
    await session.commit()

    # Forward to open_agent
    payload: dict = {
        "system_prompt": system_prompt,
        "message": message,
        "history": history,
    }
    if file_data:
        payload["file"] = file_data

    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="open_agent",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("sudamerica:chat",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    try:
        response = await internal_http.post(
            f"{settings.SERVICE_OPEN_AGENT_URL}/api/v1/agent/chat",
            json=payload,
            headers=headers,
            timeout=90.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Failed to forward sudamerica message to open_agent")
        raise

    result = response.json()
    response_text = result.get("response", "")
    tokens_used = result.get("tokens_used", 0)
    model_used = result.get("model_used", "")

    # Re-set RLS context (SET LOCAL lost after commit)
    await set_tenant_context(session, str(tenant_id))

    # Save assistant response
    await _save_message(
        session, tenant_id, usuario_id,
        "assistant", response_text, tokens_used, model_used,
    )
    await session.commit()

    return {
        "response": response_text,
        "tokens_used": tokens_used,
        "model_used": model_used,
        "tools_used": result.get("tools_used", []),
    }
