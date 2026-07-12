"""Service for the user-facing agent config (dashboard).

api_execute owns ``agente_config``. This module reads/writes the full config row
for a tenant, auto-creating a default row on first read (mirrors the old
AI_dialer ``get_config(auto_create=True)`` behavior).
"""

import json
from uuid import UUID

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import set_tenant_context

# Columns exposed by AgenteConfigResponse (order-independent). ``menu_cabecera_url``
# is intentionally excluded — it is queried elsewhere but has no DDL yet.
_CONFIG_COLUMNS = (
    "id, tenant_id, system_prompt, modelo, temperatura, max_tokens, voz_id, "
    "voz_nombre, umbral_confianza, sub_agentes_activos, auto_respuesta_whatsapp, "
    "outbound_proactivo, outbound_horario_inicio, outbound_horario_fin, "
    "outbound_mensaje_template, instrucciones_disponibilidad, knowledge_max_chars, "
    "session_timeout_minutes, nombre_agente, personalidad, menu_pdf_url, "
    "debounce_seconds, activo"
)

# Columns that may be PATCHed by the dashboard (name -> is JSONB).
_UPDATABLE_COLUMNS = {
    "system_prompt": False,
    "modelo": False,
    "temperatura": False,
    "max_tokens": False,
    "voz_id": False,
    "voz_nombre": False,
    "umbral_confianza": False,
    "sub_agentes_activos": True,
    "auto_respuesta_whatsapp": False,
    "outbound_proactivo": False,
    "outbound_horario_inicio": False,
    "outbound_horario_fin": False,
    "outbound_mensaje_template": False,
    "instrucciones_disponibilidad": False,
    "knowledge_max_chars": False,
    "session_timeout_minutes": False,
    "nombre_agente": False,
    "personalidad": False,
    "menu_pdf_url": False,
    "debounce_seconds": False,
}


def _is_sqlite(session: AsyncSession) -> bool:
    """Detect if the bound engine is SQLite (used in tests)."""
    return "sqlite" in str(session.bind.url) if session.bind else False


def _map_config_row(row) -> dict:
    """Normalize a raw ``agente_config`` row into a JSON-serializable dict."""
    data = dict(row)
    subs = data.get("sub_agentes_activos")
    if isinstance(subs, str):
        try:
            data["sub_agentes_activos"] = json.loads(subs)
        except (ValueError, TypeError):
            data["sub_agentes_activos"] = None
    return data


async def get_or_create_agente_config(session: AsyncSession, tenant_id: UUID) -> dict:
    """Return the tenant's active config, creating a default row if none exists."""
    await set_tenant_context(session, str(tenant_id))
    result = await session.execute(
        sql_text(
            f"SELECT {_CONFIG_COLUMNS} FROM agente_config "
            "WHERE tenant_id = :tid AND activo = true "
            "ORDER BY created_at LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if row is not None:
        return _map_config_row(row)

    # Auto-create: derive a friendly default system prompt from the tenant name.
    name_row = (
        await session.execute(
            sql_text("SELECT nombre FROM tenants WHERE id = :tid"),
            {"tid": str(tenant_id)},
        )
    ).mappings().first()
    tenant_name = (name_row["nombre"] if name_row else None) or "tu negocio"
    system_prompt = (
        f"Eres el asistente virtual de {tenant_name}. "
        "Ayudas a los clientes con pedidos, catalogo, reservas, horarios y "
        "delivery. Eres amable, rapido y conoces el negocio de memoria. "
        "Responde en espanol."
    )
    created = await session.execute(
        sql_text(
            "INSERT INTO agente_config (tenant_id, system_prompt) "
            f"VALUES (:tid, :sp) RETURNING {_CONFIG_COLUMNS}"
        ),
        {"tid": str(tenant_id), "sp": system_prompt},
    )
    new_row = created.mappings().first()
    await session.commit()
    await set_tenant_context(session, str(tenant_id))
    return _map_config_row(new_row)


async def update_agente_config(
    session: AsyncSession, tenant_id: UUID, patch: dict
) -> dict:
    """Apply a partial update to the tenant's active config; return the full row."""
    current = await get_or_create_agente_config(session, tenant_id)

    fields = {k: v for k, v in patch.items() if k in _UPDATABLE_COLUMNS}
    if not fields:
        return current

    sqlite = _is_sqlite(session)
    set_parts: list[str] = []
    params: dict = {"cid": str(current["id"]), "tid": str(tenant_id)}
    for name, value in fields.items():
        if _UPDATABLE_COLUMNS[name] and not sqlite:
            # JSONB column on Postgres — bind a JSON string and cast.
            set_parts.append(f"{name} = CAST(:{name} AS JSONB)")
            params[name] = json.dumps(value)
        elif _UPDATABLE_COLUMNS[name]:
            # SQLite test engine stores JSON as text.
            set_parts.append(f"{name} = :{name}")
            params[name] = json.dumps(value)
        else:
            set_parts.append(f"{name} = :{name}")
            params[name] = value
    set_parts.append("updated_at = now()" if not sqlite else "updated_at = CURRENT_TIMESTAMP")

    await set_tenant_context(session, str(tenant_id))
    updated = await session.execute(
        sql_text(
            f"UPDATE agente_config SET {', '.join(set_parts)} "
            f"WHERE id = :cid AND tenant_id = :tid RETURNING {_CONFIG_COLUMNS}"
        ),
        params,
    )
    row = updated.mappings().first()
    await session.commit()
    await set_tenant_context(session, str(tenant_id))
    return _map_config_row(row)
