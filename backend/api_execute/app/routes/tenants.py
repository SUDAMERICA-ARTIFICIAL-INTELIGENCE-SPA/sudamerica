"""Tenant routes: GET /me, PATCH /me (ADMIN only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user

from app.routes.deps import AdminWriter
from app.schemas.tenant import TenantResponse, TenantUpdate
from app.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's tenant."""
    return await tenant_service.get_tenant(db, current_user["tenant_id"])


@router.patch("/me", response_model=TenantResponse)
async def update_my_tenant(
    body: TenantUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update the current tenant (ADMIN only)."""
    data = body.model_dump(exclude_unset=True)
    return await tenant_service.update_tenant(
        db, current_user["tenant_id"], data
    )
