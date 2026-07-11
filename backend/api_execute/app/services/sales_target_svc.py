"""SalesTarget service: list, upsert."""

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from shared.schemas import PaginationParams
from shared.services import crud

from app.models.sales_target import SalesTarget


async def list_targets(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    asesor_id: str | None = None,
    periodo: str | None = None,
) -> dict:
    """List sales targets for a tenant with optional filters."""
    base = select(SalesTarget).where(
        SalesTarget.tenant_id == tenant_id,
        SalesTarget.activo.is_(True),
    )
    if asesor_id:
        base = base.where(SalesTarget.asesor_id == uuid.UUID(asesor_id))
    if periodo:
        base = base.where(SalesTarget.periodo == periodo)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0

    rows = await db.execute(
        base.order_by(SalesTarget.periodo.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    items = list(rows.scalars().all())
    total_pages = max(1, math.ceil(total / pagination.page_size))

    return {
        "success": True,
        "data": items,
        "error": None,
        "meta": {
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": total_pages,
        },
    }


async def upsert_target(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
) -> SalesTarget:
    """Create or update a sales target (upsert by tenant+asesor+periodo)."""
    if data.get("asesor_id") is not None:
        await crud.require_exists(db, Usuario, tenant_id, data["asesor_id"], label="Usuario")

    query = select(SalesTarget).where(
        SalesTarget.tenant_id == tenant_id,
        SalesTarget.periodo == data["periodo"],
        SalesTarget.activo.is_(True),
    )
    if data.get("asesor_id"):
        query = query.where(SalesTarget.asesor_id == data["asesor_id"])
    else:
        query = query.where(SalesTarget.asesor_id.is_(None))

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.meta_ventas = data["meta_ventas"]
        existing.meta_leads = data["meta_leads"]
        existing.meta_conversion = data["meta_conversion"]
        await db.flush()
        return existing

    target = SalesTarget(tenant_id=tenant_id, **data)
    db.add(target)
    await db.flush()
    return target


