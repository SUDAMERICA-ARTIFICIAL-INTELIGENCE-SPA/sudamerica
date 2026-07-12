"""Tenant service: get, update, slug generation."""

import re
import uuid
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enums import TenantPlan
from shared.utils.exceptions import NotFoundError

from app.models.tenant import Tenant
from app.schemas.tenant_config import validate_tenant_config


def generate_slug(nombre: str) -> str:
    """Generate a URL-safe slug from tenant name."""
    slug = nombre.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}"


def _normalize_plan(raw_plan: str) -> TenantPlan:
    if raw_plan == TenantPlan.FREE.value:
        return TenantPlan.ESTANDAR
    return TenantPlan(raw_plan)


def _merge_dicts(base: dict, updates: Mapping[str, object]) -> dict:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _merge_dicts(
                dict(merged[key]),  # type: ignore[arg-type]
                value,
            )
        else:
            merged[key] = value
    return merged


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    """Get a tenant by ID or raise NotFoundError."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
) -> Tenant:
    """Update tenant fields. If plan changes, update limits."""
    tenant = await get_tenant(db, tenant_id)
    for key, value in data.items():
        if value is not None:
            if key == "config" and isinstance(value, Mapping):
                validate_tenant_config(dict(value))  # fail-closed: rubro inválido → 422
                tenant.config = _merge_dicts(tenant.config or {}, value)
            else:
                setattr(tenant, key, value)

    if "plan" in data and data["plan"] is not None:
        plan = _normalize_plan(data["plan"])
        tenant.plan = plan.value
        tenant.max_users = plan.max_users
        tenant.max_leads_mes = plan.max_leads_mes

    await db.flush()
    return tenant
