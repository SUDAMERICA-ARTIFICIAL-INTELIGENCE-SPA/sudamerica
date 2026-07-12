"""Admin service — business logic for SUPERADMIN endpoints."""

import importlib
import inspect as pyinspect
import itertools
import json as _json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum

import bcrypt
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# In-memory reset tokens: {token: (user_id, hashed_password, expires_at)}
_reset_tokens: dict[str, tuple[uuid.UUID, str, datetime]] = {}
_RESET_TOKEN_TTL_MINUTES = 15

from shared.models.base import Base
from shared.models.enums import (
    CanalOrigen,
    ComandaEstado,
    LeadCanal,
    LeadEstado,
    ModifierGroupTipo,
    RevisionAccion,
    RevisionDeliveryStatus,
    SubAgenteType,
    TenantPlan,
    TipoEntrega,
    UserRole,
)
from shared.models.tenant import Tenant
from shared.schemas.base import PaginatedResponse
from shared.utils.exceptions import NotFoundError, UnprocessableError

from app.models.api_key_audit import ApiKeyAudit
from app.models.lead import Lead
from app.models.platform_config import PlatformConfig
from app.models.usuario import Usuario
from app.schemas.tenant_config import RubroManifest, validate_tenant_config
from app.services.tenant_service import _merge_dicts


# ── Tenants ──────────────────────────────────────────


def _build_tenant_conditions(search: str | None, plan: str | None) -> list:
    """Build filter conditions for tenant listing."""
    conditions = []
    if search:
        conditions.append(Tenant.nombre.contains(search))
    if plan:
        conditions.append(Tenant.plan == plan)
    return conditions


def _build_tenant_query(conditions: list, page: int, page_size: int):
    """Build the ORM query for tenants with user/lead count subqueries."""
    user_sub = (
        select(Usuario.tenant_id, func.count().label("cnt"))
        .where(Usuario.activo.is_(True))
        .group_by(Usuario.tenant_id)
        .subquery("uc")
    )
    lead_sub = (
        select(Lead.tenant_id, func.count().label("cnt"))
        .group_by(Lead.tenant_id)
        .subquery("lc")
    )
    query = (
        select(
            Tenant,
            func.coalesce(user_sub.c.cnt, 0).label("user_count"),
            func.coalesce(lead_sub.c.cnt, 0).label("lead_count"),
        )
        .outerjoin(user_sub, user_sub.c.tenant_id == Tenant.id)
        .outerjoin(lead_sub, lead_sub.c.tenant_id == Tenant.id)
    )
    for cond in conditions:
        query = query.where(cond)
    return query.order_by(Tenant.created_at.desc()).offset((page - 1) * page_size).limit(page_size)


def _serialize_tenant_row(tenant, user_count: int, lead_count: int) -> dict:
    """Serialize a tenant ORM row with counts into a dict."""
    config = tenant.config
    if isinstance(config, str):
        try:
            config = _json.loads(config)
        except (ValueError, TypeError):
            config = None
    return {
        "id": tenant.id, "nombre": tenant.nombre, "slug": tenant.slug,
        "plan": tenant.plan, "max_users": tenant.max_users,
        "max_leads_mes": tenant.max_leads_mes,
        "stripe_customer_id": tenant.stripe_customer_id,
        "stripe_subscription_id": tenant.stripe_subscription_id,
        "config": config, "activo": tenant.activo,
        "created_at": tenant.created_at, "updated_at": tenant.updated_at,
        "user_count": user_count, "lead_count": lead_count,
    }


async def list_tenants(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    plan: str | None = None,
) -> PaginatedResponse:
    """List all tenants with user/lead counts (ORM-safe, no f-string SQL)."""
    conditions = _build_tenant_conditions(search, plan)

    count_q = select(func.count()).select_from(Tenant)
    for cond in conditions:
        count_q = count_q.where(cond)
    total = (await db.execute(count_q)).scalar() or 0

    query = _build_tenant_query(conditions, page, page_size)
    rows = await db.execute(query)
    items = [_serialize_tenant_row(t, uc, lc) for t, uc, lc in rows.all()]
    return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Get a single tenant with counts (ORM + correlated subqueries)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))

    user_count = (await db.execute(
        select(func.count()).where(Usuario.tenant_id == tenant_id, Usuario.activo.is_(True))
    )).scalar() or 0
    lead_count = (await db.execute(
        select(func.count()).where(Lead.tenant_id == tenant_id)
    )).scalar() or 0

    return {
        "id": tenant.id, "nombre": tenant.nombre, "slug": tenant.slug,
        "plan": tenant.plan, "max_users": tenant.max_users,
        "max_leads_mes": tenant.max_leads_mes,
        "stripe_customer_id": tenant.stripe_customer_id,
        "stripe_subscription_id": tenant.stripe_subscription_id,
        "config": tenant.config, "activo": tenant.activo,
        "created_at": tenant.created_at, "updated_at": tenant.updated_at,
        "user_count": user_count, "lead_count": lead_count,
    }


async def update_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> dict:
    """Update tenant fields."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))

    for key, value in data.items():
        if key == "config" and isinstance(value, dict):
            # Unifica a MERGE (H-9): antes hacía reemplazo total y podía borrar
            # rubro/billing por accidente. Fail-closed: rubro inválido → 422.
            validate_tenant_config(value)
            base = tenant.config if isinstance(tenant.config, dict) else {}
            tenant.config = _merge_dicts(base, value)
        elif hasattr(tenant, key):
            setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)
    return await get_tenant(db, tenant_id)


async def deactivate_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Soft-delete a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))
    tenant.activo = False
    await db.commit()


# ── Users ────────────────────────────────────────────


async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    role: str | None = None,
    tenant_id: uuid.UUID | None = None,
) -> PaginatedResponse:
    """List all users across tenants (ORM-safe, no f-string SQL)."""
    conditions = []
    if search:
        conditions.append(Usuario.email.contains(search))
    if role:
        conditions.append(Usuario.role == role)
    if tenant_id:
        conditions.append(Usuario.tenant_id == tenant_id)

    count_q = select(func.count()).select_from(Usuario)
    for cond in conditions:
        count_q = count_q.where(cond)
    total = (await db.execute(count_q)).scalar() or 0

    query = (
        select(
            Usuario.id, Usuario.tenant_id, Usuario.email,
            Usuario.nombre, Usuario.apellido, Usuario.role,
            Usuario.email_verified, Usuario.activo,
            Usuario.created_at, Usuario.updated_at,
            Tenant.nombre.label("tenant_nombre"),
        )
        .outerjoin(Tenant, Tenant.id == Usuario.tenant_id)
    )
    for cond in conditions:
        query = query.where(cond)
    query = query.order_by(Usuario.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    rows = await db.execute(query)
    items = [dict(row._mapping) for row in rows.all()]
    return PaginatedResponse.build(
        items=items, total=total, page=page, page_size=page_size
    )


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get a single user with tenant name (2 queries, ORM-safe)."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", str(user_id))

    tenant_nombre = (await db.execute(
        select(Tenant.nombre).where(Tenant.id == user.tenant_id)
    )).scalar_one_or_none()

    return {
        "id": user.id, "tenant_id": user.tenant_id,
        "email": user.email, "nombre": user.nombre,
        "apellido": user.apellido, "role": user.role,
        "email_verified": user.email_verified, "activo": user.activo,
        "created_at": user.created_at, "updated_at": user.updated_at,
        "tenant_nombre": tenant_nombre,
    }


async def update_user(
    db: AsyncSession, user_id: uuid.UUID, data: dict
) -> dict:
    """Update user fields."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", str(user_id))

    for key, value in data.items():
        if hasattr(user, key):
            setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return await get_user(db, user_id)


async def reset_password(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[str, str, datetime]:
    """Generate a temporary password, set it on the user, and return a reset token."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", str(user_id))

    temp_password = secrets.token_urlsafe(12)
    hashed = bcrypt.hashpw(
        temp_password.encode(), bcrypt.gensalt(12)
    ).decode()

    # Set temp password directly so the user can login immediately
    user.hashed_password = hashed

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES)
    _reset_tokens[token] = (user_id, hashed, expires_at)
    _purge_expired_tokens()

    await db.commit()
    logger.info("Password reset for user %s — temp password set", user_id)
    return token, temp_password, expires_at


async def set_password_with_token(
    db: AsyncSession, reset_token: str, new_password: str
) -> None:
    """Consume a reset token and set the new password."""
    _purge_expired_tokens()
    entry = _reset_tokens.pop(reset_token, None)
    if entry is None:
        raise NotFoundError("ResetToken", reset_token)

    user_id, _unused_hash, expires_at = entry
    if datetime.now(UTC) > expires_at:
        raise NotFoundError("ResetToken", "expired")

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", str(user_id))

    user.hashed_password = bcrypt.hashpw(
        new_password.encode(), bcrypt.gensalt(12)
    ).decode()
    await db.commit()
    logger.info("Password set via reset token for user %s", user_id)


def _purge_expired_tokens() -> None:
    """Remove expired tokens from the in-memory store."""
    now = datetime.now(UTC)
    expired = [k for k, v in _reset_tokens.items() if v[2] < now]
    for k in expired:
        _reset_tokens.pop(k, None)


# ── Metrics ──────────────────────────────────────────


async def get_metrics_overview(db: AsyncSession) -> dict:
    """Get platform-wide metrics overview."""
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    active_tenants = (
        await db.execute(
            select(func.count()).where(Tenant.activo.is_(True))
        )
    ).scalar() or 0
    total_users = (await db.execute(select(func.count()).select_from(Usuario))).scalar() or 0

    total_leads_month = (
        await db.execute(
            select(func.count()).where(Lead.created_at >= month_start)
        )
    ).scalar() or 0

    # Conversations today — try/except in case table doesn't exist
    total_conversations_today = 0
    try:
        r = await db.execute(
            text("SELECT count(*) FROM ai_conversations WHERE created_at >= :today"),
            {"today": today_start},
        )
        total_conversations_today = r.scalar() or 0
    except Exception:
        pass

    # MRR = PRO tenants × $15
    pro_count = (
        await db.execute(
            select(func.count()).where(Tenant.plan == "PRO", Tenant.activo.is_(True))
        )
    ).scalar() or 0
    mrr = pro_count * 15.0

    # Active WhatsApp instances
    active_wa = 0
    try:
        r = await db.execute(
            text("SELECT count(*) FROM evolution_instances WHERE status = 'CONNECTED'")
        )
        active_wa = r.scalar() or 0
    except Exception:
        pass

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_users": total_users,
        "total_leads_month": total_leads_month,
        "total_conversations_today": total_conversations_today,
        "mrr": mrr,
        "active_whatsapp_instances": active_wa,
    }


async def get_metrics_timeseries(
    db: AsyncSession, days: int = 30
) -> list[dict]:
    """Get daily metrics for the last N days (single query with generate_series)."""
    now = datetime.now(UTC)
    start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        result = await db.execute(
            text(
                "SELECT "
                "  d.day::date AS date, "
                "  (SELECT count(*) FROM tenants "
                "   WHERE created_at < d.day + interval '1 day') AS tenants, "
                "  (SELECT count(*) FROM leads "
                "   WHERE created_at >= d.day "
                "   AND created_at < d.day + interval '1 day') AS leads, "
                "  (SELECT count(*) FROM ai_conversations "
                "   WHERE created_at >= d.day "
                "   AND created_at < d.day + interval '1 day') AS conversations "
                "FROM generate_series(:start::date, :end::date, '1 day') AS d(day) "
                "ORDER BY d.day"
            ),
            {"start": start, "end": end},
        )
        return [
            {
                "date": str(row["date"]),
                "tenants": row["tenants"],
                "leads": row["leads"],
                "conversations": row["conversations"],
            }
            for row in result.mappings().all()
        ]
    except Exception:
        logger.warning("generate_series not available, using fallback", exc_info=True)
        return await _timeseries_fallback(db, days)


async def get_top_tenants(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get top tenants by lead count (single query with JOINs)."""
    result = await db.execute(
        text(
            "SELECT t.id AS tenant_id, t.nombre AS tenant_nombre, t.plan, "
            "COALESCE(lc.cnt, 0) AS leads, "
            "COALESCE(uc.cnt, 0) AS users, "
            "COALESCE(cc.cnt, 0) AS conversations "
            "FROM tenants t "
            "LEFT JOIN ("
            "  SELECT tenant_id, count(*) AS cnt FROM leads GROUP BY tenant_id"
            ") lc ON lc.tenant_id = t.id "
            "LEFT JOIN ("
            "  SELECT tenant_id, count(*) AS cnt FROM usuarios "
            "  WHERE activo = true GROUP BY tenant_id"
            ") uc ON uc.tenant_id = t.id "
            "LEFT JOIN ("
            "  SELECT tenant_id, count(*) AS cnt FROM ai_conversations "
            "  GROUP BY tenant_id"
            ") cc ON cc.tenant_id = t.id "
            "WHERE t.activo = true "
            "ORDER BY leads DESC "
            "LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row) for row in result.mappings().all()]


def _assemble_timeseries(
    start: datetime, days: int, base_tenants: int,
    tenant_by_day: dict[str, int],
    lead_by_day: dict[str, int],
    conv_by_day: dict[str, int],
) -> list[dict]:
    """Build daily timeseries points with cumulative tenants."""
    keys = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    daily_tenants = [tenant_by_day.get(k, 0) for k in keys]
    cumulative = list(itertools.accumulate(daily_tenants, initial=base_tenants))[1:]
    return [
        {
            "date": keys[i],
            "tenants": cumulative[i],
            "leads": lead_by_day.get(keys[i], 0),
            "conversations": conv_by_day.get(keys[i], 0),
        }
        for i in range(days)
    ]


def _group_by_day(timestamps) -> dict[str, int]:
    """Aggregate a list of timestamps into per-day counts."""
    counts: dict[str, int] = {}
    for ts in timestamps:
        key = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        counts[key] = counts.get(key, 0) + 1
    return counts


async def _timeseries_fallback(db: AsyncSession, days: int) -> list[dict]:
    """SQLite-compatible timeseries fallback (3 queries instead of 3N)."""
    now = datetime.now(UTC)
    start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Batch query 1: cumulative tenants per day (one query)
    tenant_rows = (await db.execute(
        select(Tenant.created_at).where(Tenant.created_at >= start)
    )).scalars().all()

    # Batch query 2: leads per day (one query)
    lead_rows = (await db.execute(
        select(Lead.created_at).where(Lead.created_at >= start)
    )).scalars().all()

    # Batch query 3: total tenants before the range (one query for cumulative base)
    base_tenants = (await db.execute(
        select(func.count()).where(Tenant.created_at < start)
    )).scalar() or 0

    # Batch query 4: conversations per day (one query, graceful)
    conv_dates: list = []
    try:
        r = await db.execute(
            text("SELECT created_at FROM ai_conversations WHERE created_at >= :start"),
            {"start": start},
        )
        conv_dates = [row[0] for row in r.all()]
    except Exception:
        pass

    # Build per-day counts from raw timestamps
    tenant_by_day = _group_by_day(tenant_rows)
    lead_by_day = _group_by_day(lead_rows)
    conv_by_day = _group_by_day(conv_dates)

    return _assemble_timeseries(
        start, days, base_tenants, tenant_by_day, lead_by_day, conv_by_day,
    )


# ── API Key Audit ────────────────────────────────────


async def log_key_action(
    db: AsyncSession,
    provider: str,
    action: str,
    performed_by: uuid.UUID | None,
    old_key_masked: str | None = None,
    new_key_masked: str | None = None,
    reason: str | None = None,
) -> None:
    """Log an API key action to audit trail."""
    entry = ApiKeyAudit(
        provider=provider,
        action=action,
        performed_by=performed_by,
        old_key_masked=old_key_masked,
        new_key_masked=new_key_masked,
        reason=reason,
    )
    db.add(entry)
    await db.commit()


def mask_key(key: str) -> str:
    """Mask an API key, showing only first 4 and last 4 chars."""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


async def upsert_platform_config(
    db: AsyncSession,
    key: str,
    value: str,
    updated_by: uuid.UUID | None = None,
) -> PlatformConfig:
    """Create or update a platform config value."""
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    config = result.scalar_one_or_none()

    if config:
        config.value = value
        config.updated_by = updated_by
    else:
        config = PlatformConfig(key=key, value=value, updated_by=updated_by)
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return config


# ── Rubros (manifiesto global persistido — Fase B, Paso 5) ────────────

# Columnas de la tabla `rubros` (espejo de RubroManifest + metadatos de versión).
_RUBRO_COLS = (
    "key", "nombre", "emoji", "sector", "labels", "capacidades",
    "sub_entidad_label", "recurso", "variantes", "precio_medida",
    "categorias_semilla", "version", "updated_at", "updated_by",
)
# Campos que el CRUD admin puede editar en runtime (la `key` es inmutable: es la PK y el
# identificador del roster; crear rubros nuevos es Paso 6+).
_RUBRO_EDITABLE = frozenset({
    "nombre", "emoji", "sector", "labels", "capacidades",
    "sub_entidad_label", "recurso", "variantes", "precio_medida",
    "categorias_semilla",
})
# Columnas JSONB: el driver puede devolverlas ya deserializadas (dict/list) o como str.
_RUBRO_JSON_COLS = ("labels", "capacidades", "categorias_semilla")


def _rubro_row_to_dict(row) -> dict:
    """Normaliza una fila de `rubros` a dict, deserializando los JSONB si llegan como str."""
    data = dict(row)
    for col in _RUBRO_JSON_COLS:
        value = data.get(col)
        if isinstance(value, str):
            data[col] = _json.loads(value)
    return data


async def list_rubros(db: AsyncSession) -> list[dict]:
    """Lista todos los rubros de la tabla global (orden por `key`)."""
    result = await db.execute(
        text("SELECT " + ", ".join(_RUBRO_COLS) + " FROM rubros ORDER BY key")
    )
    return [_rubro_row_to_dict(r) for r in result.mappings().all()]


async def get_rubro(db: AsyncSession, key: str) -> dict:
    """Un rubro por `key` (404 vía NotFoundError si no existe)."""
    result = await db.execute(
        text("SELECT " + ", ".join(_RUBRO_COLS) + " FROM rubros WHERE key = :k"),
        {"k": key},
    )
    row = result.mappings().first()
    if row is None:
        raise NotFoundError("Rubro", key)
    return _rubro_row_to_dict(row)


def _manifest_from_row(row: dict) -> dict:
    """Proyección del `RubroManifest` desde una fila (sin metadatos de versión)."""
    return {
        "key": row["key"],
        "nombre": row["nombre"],
        "emoji": row["emoji"],
        "sector": row["sector"],
        "labels": dict(row["labels"]),
        "capacidades": list(row["capacidades"]),
        "sub_entidad_label": row["sub_entidad_label"],
        "recurso": bool(row["recurso"]),
        "variantes": bool(row["variantes"]),
        "precio_medida": bool(row["precio_medida"]),
        "categorias_semilla": list(row["categorias_semilla"]),
    }


async def _bump_manifest_version(db: AsyncSession) -> int:
    """Incrementa el contador global `rubro_manifest_version` en `platform_config`.

    No commitea: el llamador (``update_rubro``) hace un único commit atómico con la fila.
    """
    result = await db.execute(
        text("SELECT value FROM platform_config WHERE key = 'rubro_manifest_version'")
    )
    value = result.scalar_one_or_none()
    current = 1
    if value is not None:
        data = value if isinstance(value, dict) else _json.loads(value)
        current = int(data.get("version", 1))
    new_version = current + 1
    await db.execute(
        text(
            "INSERT INTO platform_config (key, value) "
            "VALUES ('rubro_manifest_version', CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()"
        ),
        {"v": _json.dumps({"version": new_version})},
    )
    return new_version


async def update_rubro(
    db: AsyncSession,
    key: str,
    patch: dict,
    updated_by: uuid.UUID | None = None,
) -> dict:
    """Edita un rubro en runtime con validación fail-closed (Fase B, Paso 5).

    Reglas:
    - ``labels`` se **fusiona** con las existentes (permite editar una primitiva sin reenviar
      las 12 y seguir pasando el validador de completitud). El resto de campos editables se
      **reemplazan** si vienen en el patch. La ``key`` es inmutable.
    - El manifiesto resultante se valida contra ``RubroManifest`` (labels completos +
      capacidades conocidas): inválido ⇒ ``UnprocessableError`` (**422**) y la tabla no se toca.
    - Persiste la fila (``version`` +1), **bumpea** el contador global ``rubro_manifest_version``,
      commitea una sola vez y **refresca** el registro en proceso para servir la nueva definición
      sin redeploy.
    """
    current = await get_rubro(db, key)  # 404 si no existe
    manifest = _manifest_from_row(current)

    for field, value in patch.items():
        if field not in _RUBRO_EDITABLE:
            continue  # ignora campos no editables (p.ej. `key`, `version`) en vez de romper
        if value is None:
            continue
        if field == "labels" and isinstance(value, dict):
            merged = dict(manifest["labels"])
            merged.update(value)
            manifest["labels"] = merged
        else:
            manifest[field] = value

    # Fail-closed: valida el manifiesto COMPLETO resultante (reusa el contrato del Paso 4).
    try:
        validated = RubroManifest(**manifest)
    except ValidationError as exc:
        msg = exc.errors()[0].get("msg", "manifiesto inválido")
        raise UnprocessableError(f"rubro inválido: {msg}") from exc

    await db.execute(
        text(
            "UPDATE rubros SET "
            "nombre = :nombre, emoji = :emoji, sector = :sector, "
            "labels = CAST(:labels AS jsonb), capacidades = CAST(:capacidades AS jsonb), "
            "sub_entidad_label = :sub_entidad_label, recurso = :recurso, "
            "variantes = :variantes, precio_medida = :precio_medida, "
            "categorias_semilla = CAST(:categorias_semilla AS jsonb), "
            "version = version + 1, updated_at = NOW(), updated_by = :updated_by "
            "WHERE key = :key"
        ),
        {
            "key": key,
            "nombre": validated.nombre,
            "emoji": validated.emoji,
            "sector": validated.sector,
            "labels": _json.dumps(validated.labels),
            "capacidades": _json.dumps(validated.capacidades),
            "sub_entidad_label": validated.sub_entidad_label,
            "recurso": validated.recurso,
            "variantes": validated.variantes,
            "precio_medida": validated.precio_medida,
            "categorias_semilla": _json.dumps(validated.categorias_semilla),
            "updated_by": str(updated_by) if updated_by else None,
        },
    )
    await _bump_manifest_version(db)
    await db.commit()

    # Refresca el caché en proceso: la nueva definición y versión se sirven de inmediato.
    from app.services import rubro_registry

    await rubro_registry.refresh(db)
    logger.info("Rubro %s editado por %s; manifest_version bumpeado.", key, updated_by)
    return await get_rubro(db, key)


DATA_MODEL_MODULES = (
    "shared.models.tenant",
    "app.models.api_key_audit",
    "app.models.categoria",
    "app.models.comanda",
    "app.models.lead",
    "app.models.modifier",
    "app.models.platform_config",
    "app.models.producto",
    "app.models.sales_target",
    "app.models.smart_alert",
    "app.models.stripe_event",
    "app.models.usuario",
    "app.models.venta",
)

DATA_MODEL_ENUMS: tuple[type[Enum], ...] = (
    UserRole,
    TenantPlan,
    LeadCanal,
    LeadEstado,
    RevisionAccion,
    RevisionDeliveryStatus,
    SubAgenteType,
    TipoEntrega,
    CanalOrigen,
    ComandaEstado,
    ModifierGroupTipo,
)


def _load_data_model_modules() -> None:
    """Import all SQLAlchemy model modules used by the admin schema viewer."""
    for module_name in DATA_MODEL_MODULES:
        importlib.import_module(module_name)


def _build_model_lookup() -> dict[str, tuple[str | None, str | None]]:
    """Map DB table names to SQLAlchemy model names and short descriptions."""
    lookup: dict[str, tuple[str | None, str | None]] = {}

    for mapper in Base.registry.mappers:
        description = pyinspect.getdoc(mapper.class_)
        lookup[mapper.local_table.name] = (
            mapper.class_.__name__,
            description.splitlines()[0] if description else None,
        )

    return lookup


def _serialize_default(value: object) -> str | None:
    """Convert dialect-specific defaults into response-safe strings."""
    if value is None:
        return None
    return str(value)


def _extract_unique_columns(unique_constraints, indexes) -> set[str]:
    """Extract single-column unique constraints from constraints and indexes."""
    result = {
        cols[0]
        for c in unique_constraints
        if (cols := c.get("column_names") or []) and len(cols) == 1
    }
    for idx in indexes:
        cols = idx.get("column_names") or []
        if idx.get("unique") and len(cols) == 1:
            result.add(cols[0])
    return result


def _build_fk_map(constrained: list, referred: list, ref_table: str) -> dict[str, str]:
    """Map constrained columns to their foreign key targets."""
    default_ref = referred[0] if referred else ""
    return {
        col: f"{ref_table}.{referred[i] if i < len(referred) else default_ref}"
        if (referred[i] if i < len(referred) else default_ref) else ref_table
        for i, col in enumerate(constrained)
    }


def _extract_relations(foreign_keys) -> tuple[list[dict], dict[str, str]]:
    """Parse foreign keys into relations list and column→target map."""
    relations: list[dict] = []
    fk_map: dict[str, str] = {}
    for fk in foreign_keys:
        constrained = fk.get("constrained_columns") or []
        referred = fk.get("referred_columns") or []
        ref_table = fk.get("referred_table")
        if not constrained or not ref_table:
            continue
        relations.append({
            "column": ", ".join(constrained),
            "references_table": ref_table,
            "references_column": ", ".join(referred),
            "on_delete": (fk.get("options") or {}).get("ondelete"),
        })
        fk_map.update(_build_fk_map(constrained, referred, ref_table))
    return relations, fk_map


def _serialize_columns(columns, pk_columns, unique_columns, fk_map) -> list[dict]:
    """Serialize raw inspector columns into response dicts."""
    return [
        {
            "name": c["name"],
            "type": str(c["type"]),
            "nullable": bool(c.get("nullable", True)),
            "primary_key": c["name"] in pk_columns,
            "unique": c["name"] in unique_columns,
            "default": _serialize_default(c.get("default")),
            "foreign_key": fk_map.get(c["name"]),
        }
        for c in columns
    ]


def _constraints_to_indexes(unique_constraints, table_name) -> list[dict]:
    """Convert unique constraints to index-like dicts."""
    return [
        {
            "name": c.get("name") or f"{table_name}_{'_'.join(c.get('column_names') or ['idx'])}_key",
            "column_names": c.get("column_names") or [],
            "unique": True,
        }
        for c in unique_constraints
        if c.get("column_names")
    ]


def _dedup_indexes(indexes, unique_constraints, table_name) -> list[dict]:
    """Merge indexes + unique constraints and deduplicate."""
    raw = list(indexes) + _constraints_to_indexes(unique_constraints, table_name)
    seen: set[tuple[str, tuple[str, ...], bool]] = set()
    result: list[dict] = []
    for idx in raw:
        cols = tuple(idx.get("column_names") or [])
        sig = (idx.get("name") or "", cols, bool(idx.get("unique")))
        if sig not in seen:
            seen.add(sig)
            result.append({"name": idx.get("name") or ", ".join(cols), "columns": list(cols), "unique": bool(idx.get("unique"))})
    return result


def _inspect_table(inspector, table_name, model_lookup) -> dict:
    """Inspect a single table and return its serialized schema."""
    columns = inspector.get_columns(table_name)
    pk_cols = set((inspector.get_pk_constraint(table_name) or {}).get("constrained_columns") or [])
    fks = inspector.get_foreign_keys(table_name)
    ucs = inspector.get_unique_constraints(table_name)
    idxs = inspector.get_indexes(table_name)

    unique_cols = _extract_unique_columns(ucs, idxs)
    relations, fk_map = _extract_relations(fks)
    table_columns = _serialize_columns(columns, pk_cols, unique_cols, fk_map)
    deduped = _dedup_indexes(idxs, ucs, table_name)

    model_name, description = model_lookup.get(table_name, (None, None))
    return {
        "name": table_name,
        "model_name": model_name,
        "description": description,
        "tenant_scoped": any(c["name"] == "tenant_id" for c in table_columns),
        "has_soft_delete": any(c["name"] == "activo" for c in table_columns),
        "columns": table_columns,
        "relations": relations,
        "indexes": deduped,
    }


def _collect_data_model(sync_connection) -> dict:
    """Inspect the active database schema and serialize its current shape."""
    inspector = inspect(sync_connection)
    model_lookup = _build_model_lookup()
    table_names = sorted(
        name for name in inspector.get_table_names() if not name.startswith("sqlite_")
    )

    tables = [_inspect_table(inspector, name, model_lookup) for name in table_names]
    total_columns = sum(len(t["columns"]) for t in tables)
    total_rels = sum(len(t["relations"]) for t in tables)
    tenant_scoped = sum(1 for t in tables if t["tenant_scoped"])

    return {
        "generated_at": datetime.now(UTC),
        "summary": {
            "total_tables": len(tables),
            "total_columns": total_columns,
            "tenant_scoped_tables": tenant_scoped,
            "total_relationships": total_rels,
        },
        "enums": [
            {"name": e.__name__, "values": [m.value for m in e]}
            for e in DATA_MODEL_ENUMS
        ],
        "tables": tables,
    }


async def get_data_model_snapshot(db: AsyncSession) -> dict:
    """Return the current database schema snapshot for SUPERADMIN users."""
    _load_data_model_modules()
    connection = await db.connection()
    return await connection.run_sync(_collect_data_model)
