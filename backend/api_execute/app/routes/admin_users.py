"""Admin user management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db
from shared.schemas.base import PaginatedResponse

from app.routes.deps import SuperAdminOnly
from app.schemas.admin import (
    ResetPasswordResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    UserAdminResponse,
    UserAdminUpdate,
)
from app.services import admin_service

router = APIRouter(prefix="/users", tags=["admin-users"])


@router.get("", response_model=PaginatedResponse[UserAdminResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    tenant_id: UUID | None = None,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """List all users across tenants."""
    return await admin_service.list_users(db, page, page_size, search, role, tenant_id)


@router.get("/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: UUID,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Get user detail."""
    return await admin_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: UUID,
    body: UserAdminUpdate,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Update user."""
    data = body.model_dump(exclude_unset=True)
    return await admin_service.update_user(db, user_id, data)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: UUID,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Reset password and return a temporary one."""
    token, temp_password, expires_at = await admin_service.reset_password(db, user_id)
    return ResetPasswordResponse(reset_token=token, temp_password=temp_password, expires_at=expires_at)


@router.post("/set-password", response_model=SetPasswordResponse)
async def set_password(
    body: SetPasswordRequest,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Set password using a one-time reset token."""
    await admin_service.set_password_with_token(db, body.reset_token, body.new_password)
    return SetPasswordResponse(status="password_updated")
