"""Service for the dashboard knowledge base + training (tenant_knowledge).

api_execute owns ``tenant_knowledge``. CRUD is plain tenant-scoped SQL; ``teach``
and ``test`` reuse ``open_agent /api/v1/agent/generate`` (no tools) for the LLM
bits, degrading gracefully when the LLM is unavailable. The "RAG" here is text
injection of the tenant's active knowledge — ``ai_embeddings`` is NOT used.
"""

import logging
from uuid import UUID

import httpx
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import set_tenant_context
from shared.middleware import build_service_auth_headers
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)

_KNOWLEDGE_COLUMNS = (
    "id, tenant_id, type, title, content, priority, activo, created_at, updated_at"
)

_TITLE_SYSTEM_PROMPT = (
    "Extrae un titulo corto (maximo 8 palabras) del siguiente texto de "
    "conocimiento para un negocio. Responde SOLO con el titulo, sin comillas ni "
    "puntuacion extra."
)

_UPDATABLE_KNOWLEDGE_COLUMNS = ("type", "title", "content", "priority")


async def _generate(
    settings,
    tenant_id: UUID,
    system_prompt: str,
    message: str,
    *,
    max_tokens_hint: int | None = None,
) -> str:
    """Call open_agent /generate (no tools) and return the reply text.

    Raises on any transport/HTTP error so callers can decide how to degrade.
    """
    payload = {
        "system_prompt": system_prompt,
        "message": message[:8000],
        "history": [],
    }
    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="open_agent",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("generate:chat",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    response = await internal_http.post(
        f"{settings.SERVICE_OPEN_AGENT_URL}/api/v1/agent/generate",
        json=payload,
        headers=headers,
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json().get("response", "") or ""


async def list_knowledge(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    type_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """Return (active knowledge rows, total) for a tenant, newest-priority first."""
    await set_tenant_context(session, str(tenant_id))
    where = "tenant_id = :tid AND activo = true"
    params: dict = {"tid": str(tenant_id)}
    if type_filter:
        where += " AND type = :type"
        params["type"] = type_filter

    total = (
        await session.execute(
            sql_text(f"SELECT COUNT(id) FROM tenant_knowledge WHERE {where}"),  # noqa: S608
            params,
        )
    ).scalar() or 0

    params["limit_val"] = page_size
    params["offset_val"] = (page - 1) * page_size
    rows = (
        await session.execute(
            sql_text(  # noqa: S608 - fixed WHERE clause, values bound
                f"SELECT {_KNOWLEDGE_COLUMNS} FROM tenant_knowledge WHERE {where} "
                "ORDER BY priority DESC, created_at DESC "
                "LIMIT :limit_val OFFSET :offset_val"
            ),
            params,
        )
    ).mappings().all()
    return [dict(r) for r in rows], total


async def get_knowledge(
    session: AsyncSession, tenant_id: UUID, knowledge_id: UUID
) -> dict | None:
    """Return a single active knowledge row, or None."""
    await set_tenant_context(session, str(tenant_id))
    row = (
        await session.execute(
            sql_text(
                f"SELECT {_KNOWLEDGE_COLUMNS} FROM tenant_knowledge "
                "WHERE id = :kid AND tenant_id = :tid AND activo = true"
            ),
            {"kid": str(knowledge_id), "tid": str(tenant_id)},
        )
    ).mappings().first()
    return dict(row) if row else None


async def create_knowledge(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    type_: str,
    title: str,
    content: str,
    priority: int = 0,
) -> dict:
    """Insert a knowledge row and return it."""
    await set_tenant_context(session, str(tenant_id))
    row = (
        await session.execute(
            sql_text(
                "INSERT INTO tenant_knowledge (tenant_id, type, title, content, priority) "
                f"VALUES (:tid, :type, :title, :content, :priority) RETURNING {_KNOWLEDGE_COLUMNS}"
            ),
            {
                "tid": str(tenant_id),
                "type": type_,
                "title": title,
                "content": content,
                "priority": priority,
            },
        )
    ).mappings().first()
    await session.commit()
    await set_tenant_context(session, str(tenant_id))
    return dict(row)


async def update_knowledge(
    session: AsyncSession, tenant_id: UUID, knowledge_id: UUID, data: dict
) -> dict | None:
    """Apply a partial update to a knowledge row; return it or None if not found."""
    fields = {k: v for k, v in data.items() if k in _UPDATABLE_KNOWLEDGE_COLUMNS}
    await set_tenant_context(session, str(tenant_id))
    if not fields:
        return await get_knowledge(session, tenant_id, knowledge_id)

    set_parts = [f"{name} = :{name}" for name in fields]
    set_parts.append("updated_at = now()")
    params = {**fields, "kid": str(knowledge_id), "tid": str(tenant_id)}
    row = (
        await session.execute(
            sql_text(
                f"UPDATE tenant_knowledge SET {', '.join(set_parts)} "
                f"WHERE id = :kid AND tenant_id = :tid AND activo = true "
                f"RETURNING {_KNOWLEDGE_COLUMNS}"
            ),
            params,
        )
    ).mappings().first()
    await session.commit()
    await set_tenant_context(session, str(tenant_id))
    return dict(row) if row else None


async def delete_knowledge(
    session: AsyncSession, tenant_id: UUID, knowledge_id: UUID
) -> bool:
    """Soft-delete a knowledge row (activo=false); return True if a row changed."""
    await set_tenant_context(session, str(tenant_id))
    result = await session.execute(
        sql_text(
            "UPDATE tenant_knowledge SET activo = false, updated_at = now() "
            "WHERE id = :kid AND tenant_id = :tid AND activo = true"
        ),
        {"kid": str(knowledge_id), "tid": str(tenant_id)},
    )
    await session.commit()
    await set_tenant_context(session, str(tenant_id))
    return (result.rowcount or 0) > 0


async def build_knowledge_context(
    session: AsyncSession, tenant_id: UUID, *, max_chars: int = 6000
) -> str:
    """Concatenate the tenant's active knowledge into a text block for the LLM."""
    await set_tenant_context(session, str(tenant_id))
    rows = (
        await session.execute(
            sql_text(
                "SELECT title, content FROM tenant_knowledge "
                "WHERE tenant_id = :tid AND activo = true "
                "ORDER BY priority DESC, created_at DESC"
            ),
            {"tid": str(tenant_id)},
        )
    ).mappings().all()

    parts: list[str] = []
    used = 0
    for r in rows:
        block = f"## {r['title']}\n{r['content']}".strip()
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


async def teach(
    session: AsyncSession, tenant_id: UUID, content: str, settings
) -> dict:
    """Persist a training snippet, extracting a short title via the LLM.

    Degrades to a title derived from the first words of the content when the LLM
    is unavailable — the knowledge entry is still created either way.
    """
    title = ""
    try:
        title = (await _generate(settings, tenant_id, _TITLE_SYSTEM_PROMPT, content)).strip()
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.warning("teach: LLM title extraction failed; deriving title from content")

    if not title:
        title = " ".join(content.split()[:8]) or "Conocimiento"
    title = title[:255]

    entry = await create_knowledge(
        session, tenant_id, type_="training", title=title, content=content
    )
    return {
        "id": str(entry["id"]),
        "title": entry["title"],
        "content": entry["content"],
        "type": entry["type"],
    }


async def test_message(
    session: AsyncSession, tenant_id: UUID, message: str, settings
) -> dict:
    """Generate a trial answer using the tenant's knowledge (nothing persisted)."""
    context = await build_knowledge_context(session, tenant_id)
    system_prompt = (
        "Eres el asistente virtual del negocio. Responde la consulta del cliente "
        "usando UNICAMENTE el siguiente conocimiento del negocio. Si no hay "
        "informacion suficiente, dilo con honestidad.\n\n"
        f"=== CONOCIMIENTO DEL NEGOCIO ===\n{context}"
    )
    try:
        reply = await _generate(settings, tenant_id, system_prompt, message)
        return {"response": reply.strip(), "confidence": 0.90, "sub_agent": "TEST"}
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.warning("test_message: LLM generation unavailable; returning degraded reply")
        return {
            "response": (
                "No se pudo generar una respuesta de prueba: el motor de "
                "generacion (open_agent/LLM) no esta disponible. "
                "TODO: configurar OPENAI_API_KEY/GEMINI_API_KEY y open_agent."
            ),
            "confidence": 0.0,
            "sub_agent": "TEST",
        }
