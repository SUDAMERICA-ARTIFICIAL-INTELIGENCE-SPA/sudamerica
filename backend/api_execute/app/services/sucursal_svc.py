"""Sucursal service: CRUD + auto-principal + plan enforcement."""

import re
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.sucursal import Sucursal
from shared.utils.exceptions import ConflictError, ForbiddenError, NotFoundError

from app.models.tenant import Tenant

# Tables that get sucursal_id backfilled on auto-migration
_TABLES_WITH_SUCURSAL = (
    "mesas", "comandas", "reservaciones", "ventas",
    "evolution_instances", "leads", "sessions", "agente_config",
)


def generate_slug(nombre: str) -> str:
    """Generate a URL-safe slug from sucursal name."""
    slug = nombre.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}"


async def _count_active(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(Sucursal.id)).where(
            Sucursal.tenant_id == tenant_id,
            Sucursal.activo.is_(True),
        )
    )
    return result.scalar_one()


async def _enforce_plan_limit(
    db: AsyncSession, tenant_id: uuid.UUID
) -> None:
    """FREE/ESTANDAR plan: max 1 sucursal. PRO: unlimited."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))
    if tenant.plan in ("FREE", "ESTANDAR"):
        count = await _count_active(db, tenant_id)
        if count >= 1:
            raise ForbiddenError(
                "El plan Estándar permite máximo 1 sucursal. "
                "Actualiza a PRO para agregar más ubicaciones."
            )


async def _ensure_principal_exists(
    db: AsyncSession, tenant_id: uuid.UUID
) -> Sucursal | None:
    """If no principal exists, auto-create one from tenant config and migrate orphan rows."""
    result = await db.execute(
        select(Sucursal).where(
            Sucursal.tenant_id == tenant_id,
            Sucursal.es_principal.is_(True),
            Sucursal.activo.is_(True),
        )
    )
    principal = result.scalar_one_or_none()
    if principal:
        return principal

    # Auto-create principal from tenant data
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))

    config = tenant.config or {}
    principal = Sucursal(
        tenant_id=tenant_id,
        nombre="Sucursal Principal",
        slug=generate_slug("sucursal-principal"),
        direccion=config.get("direccion"),
        telefono=config.get("telefono"),
        horario=config.get("horario", {}),
        zona_delivery=config.get("zona_delivery"),
        es_principal=True,
    )
    db.add(principal)
    await db.flush()

    # Migrate orphan rows (sucursal_id IS NULL) to the new principal
    for table_name in _TABLES_WITH_SUCURSAL:
        await db.execute(
            text(
                f"UPDATE {table_name} SET sucursal_id = :sid "  # noqa: S608
                f"WHERE tenant_id = :tid AND sucursal_id IS NULL"
            ),
            {"sid": principal.id, "tid": tenant_id},
        )

    return principal


async def list_sucursales(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[Sucursal]:
    """List all active sucursales for a tenant."""
    result = await db.execute(
        select(Sucursal)
        .where(Sucursal.tenant_id == tenant_id, Sucursal.activo.is_(True))
        .order_by(Sucursal.es_principal.desc(), Sucursal.nombre)
    )
    return list(result.scalars().all())


async def get_sucursal(
    db: AsyncSession, tenant_id: uuid.UUID, sucursal_id: uuid.UUID
) -> Sucursal:
    """Get a single sucursal or raise NotFoundError."""
    result = await db.execute(
        select(Sucursal).where(
            Sucursal.id == sucursal_id,
            Sucursal.tenant_id == tenant_id,
        )
    )
    suc = result.scalar_one_or_none()
    if not suc:
        raise NotFoundError("Sucursal", str(sucursal_id))
    return suc


async def create_sucursal(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict[str, Any]
) -> Sucursal:
    """Create a new sucursal with plan enforcement and auto-principal logic."""
    count = await _count_active(db, tenant_id)

    if count == 0:
        # First sucursal — auto-set as principal
        suc = Sucursal(
            tenant_id=tenant_id,
            nombre=data["nombre"],
            slug=generate_slug(data["nombre"]),
            direccion=data.get("direccion"),
            telefono=data.get("telefono"),
            horario=data.get("horario", {}),
            zona_delivery=data.get("zona_delivery"),
            latitud=data.get("latitud"),
            longitud=data.get("longitud"),
            config=data.get("config", {}),
            es_principal=True,
        )
        db.add(suc)
        await db.flush()
        return suc

    # Creating 2nd+ sucursal — enforce plan limits
    await _enforce_plan_limit(db, tenant_id)

    # Ensure a principal exists (auto-create + migrate if needed)
    await _ensure_principal_exists(db, tenant_id)

    suc = Sucursal(
        tenant_id=tenant_id,
        nombre=data["nombre"],
        slug=generate_slug(data["nombre"]),
        direccion=data.get("direccion"),
        telefono=data.get("telefono"),
        horario=data.get("horario", {}),
        zona_delivery=data.get("zona_delivery"),
        latitud=data.get("latitud"),
        longitud=data.get("longitud"),
        config=data.get("config", {}),
        es_principal=False,
    )
    db.add(suc)
    await db.flush()
    return suc


async def update_sucursal(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sucursal_id: uuid.UUID,
    data: dict[str, Any],
) -> Sucursal:
    """PATCH update a sucursal."""
    suc = await get_sucursal(db, tenant_id, sucursal_id)
    # Regenerate slug if nombre changes
    if "nombre" in data and data["nombre"] is not None:
        data["slug"] = generate_slug(data["nombre"])
    for key, value in data.items():
        if value is not None:
            setattr(suc, key, value)
    await db.flush()
    return suc


async def deactivate_sucursal(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sucursal_id: uuid.UUID,
) -> Sucursal:
    """Soft-delete a sucursal. Cannot deactivate the principal if others exist."""
    suc = await get_sucursal(db, tenant_id, sucursal_id)
    if suc.es_principal:
        other_count = await _count_active(db, tenant_id) - 1
        if other_count > 0:
            raise ConflictError(
                "No se puede desactivar la sucursal principal mientras "
                "existan otras sucursales activas."
            )
    suc.activo = False
    await db.flush()
    return suc
