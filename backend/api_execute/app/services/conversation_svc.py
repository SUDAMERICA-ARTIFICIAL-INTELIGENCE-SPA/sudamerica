"""Service for the dashboard conversation viewer.

api_execute owns ``ai_conversations``. This module powers the thread list
(grouped by lead, newest first) and the per-lead message view (chronological
within each page). Mirrors the old AI_dialer ``conversations`` routes.
"""

from uuid import UUID

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import set_tenant_context


def _iso(value) -> str:
    """Return an ISO-8601 string for a datetime (or best-effort string)."""
    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _meta(total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1
    return {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


async def list_threads(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    canal: str | None = None,
) -> dict:
    """Return paginated conversation threads (one row per lead, newest first)."""
    await set_tenant_context(session, str(tenant_id))

    where = "c.tenant_id = :tid AND c.lead_id IS NOT NULL"
    params: dict = {"tid": str(tenant_id)}
    if canal:
        where += " AND c.canal = :canal"
        params["canal"] = canal

    total = (
        await session.execute(
            sql_text(  # noqa: S608 - interpolation is a fixed WHERE clause, values are bound
                f"SELECT COUNT(DISTINCT c.lead_id) FROM ai_conversations c WHERE {where}"
            ),
            params,
        )
    ).scalar() or 0

    params["limit_val"] = page_size
    params["offset_val"] = (page - 1) * page_size
    rows = (
        await session.execute(
            sql_text(  # noqa: S608 - see above
                "WITH ranked AS ("
                "  SELECT c.lead_id, c.content, c.role, c.canal, c.created_at, c.id,"
                "  ROW_NUMBER() OVER (PARTITION BY c.lead_id"
                "    ORDER BY c.created_at DESC, c.id DESC) AS rn,"
                "  COUNT(*) OVER (PARTITION BY c.lead_id) AS msg_count"
                f"  FROM ai_conversations c WHERE {where}"
                ") "
                "SELECT r.lead_id, r.content, r.role, r.canal, r.created_at,"
                " r.msg_count, l.nombre AS lead_name "
                "FROM ranked r "
                "LEFT JOIN leads l ON l.id = r.lead_id AND l.tenant_id = :tid "
                "WHERE r.rn = 1 "
                "ORDER BY r.created_at DESC, r.lead_id DESC "
                "LIMIT :limit_val OFFSET :offset_val"
            ),
            params,
        )
    ).mappings().all()

    threads = [
        {
            "lead_id": str(row["lead_id"]),
            "lead_name": row["lead_name"],
            "session_id": None,
            "last_message": (row["content"] or "")[:200],
            "last_role": row["role"] or "user",
            "last_canal": row["canal"],
            "message_count": row["msg_count"],
            "last_message_at": _iso(row["created_at"]),
        }
        for row in rows
    ]
    return {"data": threads, "meta": _meta(total, page, page_size)}


async def list_messages(
    session: AsyncSession,
    tenant_id: UUID,
    lead_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Return one lead's messages, chronological within the page."""
    await set_tenant_context(session, str(tenant_id))

    params = {"tid": str(tenant_id), "lid": str(lead_id)}
    total = (
        await session.execute(
            sql_text(
                "SELECT COUNT(id) FROM ai_conversations "
                "WHERE tenant_id = :tid AND lead_id = :lid"
            ),
            params,
        )
    ).scalar() or 0

    params["limit_val"] = page_size
    params["offset_val"] = (page - 1) * page_size
    rows = (
        await session.execute(
            sql_text(
                "SELECT id, role, content, canal, tokens_used, modelo, session_id,"
                " media_url, media_type, created_at "
                "FROM ai_conversations "
                "WHERE tenant_id = :tid AND lead_id = :lid "
                "ORDER BY created_at DESC, id DESC "
                "LIMIT :limit_val OFFSET :offset_val"
            ),
            params,
        )
    ).mappings().all()

    # Page 1 = latest chunk; reverse so messages read oldest -> newest for chat.
    ordered = list(rows)
    ordered.reverse()
    messages = [
        {
            "id": str(m["id"]),
            "role": m["role"],
            "content": m["content"],
            "canal": m["canal"],
            "tokens_used": m["tokens_used"],
            "modelo": m["modelo"],
            "session_id": str(m["session_id"]) if m["session_id"] else None,
            "media_url": m["media_url"],
            "media_type": m["media_type"],
            "created_at": _iso(m["created_at"]),
        }
        for m in ordered
    ]
    return {"data": messages, "meta": _meta(total, page, page_size)}
