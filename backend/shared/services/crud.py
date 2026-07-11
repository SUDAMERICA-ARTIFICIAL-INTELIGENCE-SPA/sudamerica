"""Generic tenant-scoped CRUD operations for TenantBase models."""

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from shared.models.base import TenantBase
from shared.schemas.base import PaginatedResponse
from shared.schemas.pagination import PaginationParams
from shared.utils.exceptions import NotFoundError


async def list_active(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    pagination: PaginationParams,
    *,
    extra_filters: Sequence[Any] = (),
    order_by: Any | None = None,
) -> PaginatedResponse:
    """Paginated list of active tenant-scoped records."""
    base: Select = select(model).where(
        model.tenant_id == tenant_id,
        model.activo.is_(True),
    )
    for f in extra_filters:
        base = base.where(f)

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    if order_by is None:
        order_by = model.created_at.desc()
    rows = await db.execute(
        base.order_by(order_by)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    items = list(rows.scalars().all())
    return PaginatedResponse.build(
        items=items, total=total,
        page=pagination.page, page_size=pagination.page_size,
    )


async def get_by_id(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
    require_active: bool = True,
) -> TenantBase:
    """Fetch one record by (tenant_id, id). Raises NotFoundError."""
    clauses = [model.id == item_id, model.tenant_id == tenant_id]
    if require_active:
        clauses.append(model.activo.is_(True))
    result = await db.execute(select(model).where(*clauses))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise NotFoundError(label or model.__tablename__, str(item_id))
    return obj


async def update_fields(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    data: dict[str, Any],
    *,
    label: str | None = None,
) -> TenantBase:
    """PATCH semantics: update only provided fields."""
    obj = await get_by_id(db, model, tenant_id, item_id, label=label)
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    return obj


async def soft_delete(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
) -> TenantBase:
    """Set activo=False."""
    obj = await get_by_id(db, model, tenant_id, item_id, label=label)
    obj.activo = False
    await db.flush()
    return obj


async def require_exists(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
) -> None:
    """Raise NotFoundError if (tenant_id, id, activo) row doesn't exist."""
    result = await db.execute(
        select(model.id).where(
            model.id == item_id,
            model.tenant_id == tenant_id,
            model.activo.is_(True),
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError(label or model.__tablename__, str(item_id))


async def create_one(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    data: dict[str, Any],
) -> TenantBase:
    """Create a tenant-scoped record."""
    obj = model(tenant_id=tenant_id, **data)
    db.add(obj)
    await db.flush()
    return obj


async def reactivate(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
) -> TenantBase:
    """Set activo=True (fetch even inactive records)."""
    obj = await get_by_id(
        db, model, tenant_id, item_id,
        label=label, require_active=False,
    )
    obj.activo = True
    await db.flush()
    return obj
