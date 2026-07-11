"""Admin tenant management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db
from shared.schemas.base import PaginatedResponse

from app.routes.deps import SuperAdminOnly
from app.schemas.admin import TenantAdminResponse, TenantAdminUpdate
from app.services import admin_service

router = APIRouter(prefix="/tenants", tags=["admin-tenants"])


@router.get("", response_model=PaginatedResponse[TenantAdminResponse])
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    plan: str | None = None,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """List all tenants with counts."""
    return await admin_service.list_tenants(db, page, page_size, search, plan)


@router.get("/{tenant_id}", response_model=TenantAdminResponse)
async def get_tenant(
    tenant_id: UUID,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Get tenant detail."""
    return await admin_service.get_tenant(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantAdminResponse)
async def update_tenant(
    tenant_id: UUID,
    body: TenantAdminUpdate,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Update tenant."""
    data = body.model_dump(exclude_unset=True)
    return await admin_service.update_tenant(db, tenant_id, data)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant(
    tenant_id: UUID,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete tenant."""
    await admin_service.deactivate_tenant(db, tenant_id)
