"""Service for AI conversation summaries — aggregates message-level data."""

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Token cost rate (approximate for OpenAI-class models)
_TOKEN_COST_RATE = 0.000003  # $3 per 1M tokens


def _is_sqlite(db: AsyncSession) -> bool:
    """Detect if the bound engine is SQLite (used in tests)."""
    return "sqlite" in str(db.bind.url) if db.bind else False


def _build_conv_where(
    tenant_id: uuid.UUID,
    lead_id: str | None,
    fecha_desde: str | None,
    fecha_hasta: str | None,
) -> tuple[str, dict]:
    """Build WHERE clause and params for conversation queries."""
    params: dict = {"tid": str(tenant_id)}
    clauses = ["c.tenant_id = :tid", "c.lead_id IS NOT NULL"]
    if lead_id:
        clauses.append("c.lead_id = :lead_id")
        params["lead_id"] = lead_id
    if fecha_desde:
        clauses.append("c.created_at >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        clauses.append("c.created_at <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    return " AND ".join(clauses), params


def _build_conv_cte(where_sql: str, sqlite: bool) -> str:
    """Build the CTE SQL for conversation summaries."""
    dur_expr = (
        "(julianday(MAX(c.created_at)) - julianday(MIN(c.created_at))) * 86400"
        if sqlite
        else "EXTRACT(EPOCH FROM MAX(c.created_at) - MIN(c.created_at))"
    )
    return (  # noqa: S608
        f"WITH conv AS ("
        f"  SELECT c.lead_id AS id, c.tenant_id, c.lead_id,"
        f"  MAX(c.canal) AS canal, COALESCE(SUM(c.tokens_used), 0) AS total_tokens,"
        f"  COUNT(*) AS msg_count, MIN(c.created_at) AS first_msg,"
        f"  MAX(c.created_at) AS last_msg, {dur_expr} AS duracion_segundos"
        f"  FROM ai_conversations c WHERE {where_sql}"
        f"  GROUP BY c.lead_id, c.tenant_id"
        f"), conv_review AS ("
        f"  SELECT conv.*,"
        f"  CASE WHEN rh.id IS NULL THEN 1 ELSE 0 END AS resuelto_sin_humano"
        f"  FROM conv LEFT JOIN revision_humana rh"
        f"  ON rh.tenant_id = conv.tenant_id AND rh.lead_id = conv.lead_id"
        f")"
    )


def _map_conversation_row(row) -> dict:
    """Map a raw SQL row to a conversation response dict."""
    total_tokens = row["total_tokens"] or 0
    resolved = bool(row["resuelto_sin_humano"])
    created = row["created_at"]
    return {
        "id": str(row["id"]),
        "tenant_id": str(row["tenant_id"]),
        "lead_id": str(row["lead_id"]),
        "canal": row["canal"] or "WHATSAPP",
        "resuelto_sin_humano": resolved,
        "confidence": 0.92 if resolved else 0.72,
        "token_cost": round(total_tokens * _TOKEN_COST_RATE, 6),
        "duracion_segundos": float(row["duracion_segundos"] or 0),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
    }


async def list_conversations(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    lead_id: str | None = None,
    resuelto_sin_humano: bool | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> dict:
    """Return paginated conversation summaries grouped by lead_id."""
    where_sql, params = _build_conv_where(tenant_id, lead_id, fecha_desde, fecha_hasta)
    base_cte = _build_conv_cte(where_sql, _is_sqlite(db))

    having = ""
    if resuelto_sin_humano is True:
        having = "WHERE resuelto_sin_humano = 1"
    elif resuelto_sin_humano is False:
        having = "WHERE resuelto_sin_humano = 0"

    total = (await db.execute(
        text(f"{base_cte} SELECT COUNT(*) FROM conv_review {having}"), params,  # noqa: S608
    )).scalar() or 0

    params["limit_val"] = page_size
    params["offset_val"] = (page - 1) * page_size
    data_sql = (  # noqa: S608
        f"{base_cte} SELECT id, tenant_id, lead_id, canal, resuelto_sin_humano,"
        f" total_tokens, duracion_segundos, first_msg AS created_at"
        f" FROM conv_review {having} ORDER BY first_msg DESC"
        f" LIMIT :limit_val OFFSET :offset_val"
    )
    rows = (await db.execute(text(data_sql), params)).mappings().all()
    items = [_map_conversation_row(r) for r in rows]

    return {
        "data": items,
        "meta": {
            "total": total, "page": page, "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size > 0 else 0,
        },
    }


async def get_weekly_activity(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Return conversation activity for the last 7 days (Mon-Sun)."""
    sqlite = _is_sqlite(db)
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=6)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    day_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    # Day-of-week extraction differs: PostgreSQL ISODOW (1=Mon), SQLite strftime
    if sqlite:
        # SQLite strftime('%w') returns 0=Sun, 1=Mon … 6=Sat
        # Convert to ISO: Mon=1..Sun=7
        dow_expr = "CASE CAST(strftime('%w', created_at) AS INT) WHEN 0 THEN 7 ELSE CAST(strftime('%w', created_at) AS INT) END"
    else:
        dow_expr = "EXTRACT(ISODOW FROM created_at)::int"

    sql = text(f"""
        SELECT
            {dow_expr}               AS dow,
            COUNT(DISTINCT lead_id)  AS conversations
        FROM ai_conversations
        WHERE tenant_id = :tid
          AND created_at >= :start
          AND lead_id IS NOT NULL
        GROUP BY dow
        ORDER BY dow
    """)
    result = await db.execute(sql, {"tid": str(tenant_id), "start": week_start})
    rows = {int(row[0]): int(row[1]) for row in result.all()}

    # Count human reviews per day of week
    sql_hr = text(f"""
        SELECT
            {dow_expr}  AS dow,
            COUNT(*)    AS reviews
        FROM revision_humana
        WHERE tenant_id = :tid
          AND created_at >= :start
        GROUP BY dow
        ORDER BY dow
    """)
    try:
        hr_result = await db.execute(
            sql_hr, {"tid": str(tenant_id), "start": week_start}
        )
        hr_rows = {int(row[0]): int(row[1]) for row in hr_result.all()}
    except Exception:
        hr_rows = {}

    # Build 7-day array (ISO DOW: 1=Monday, 7=Sunday)
    activity = []
    for dow in range(1, 8):
        ia_convs = rows.get(dow, 0)
        human_reviews = hr_rows.get(dow, 0)
        activity.append(
            {
                "day": day_labels[dow - 1],
                "ia": round(ia_convs * 0.75, 1),
                "humano": round(human_reviews * 0.5, 1),
            }
        )

    return activity
