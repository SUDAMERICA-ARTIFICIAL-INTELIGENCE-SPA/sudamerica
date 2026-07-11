"""Admin API key management routes."""

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db
from shared.models.tenant import Tenant

from app.routes.deps import SuperAdminOnly
from shared.schemas.base import PaginatedResponse
from app.schemas.admin import (
    PlatformKeysResponse,
    PlatformKeyInfo,
    RotateKeyRequest,
    RotateKeyResponse,
    TenantKeyResponse,
)
from app.services import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["admin-api-keys"])


@router.get("/platform", response_model=PlatformKeysResponse)
async def get_platform_keys(
    request: Request,
    _current_user: dict = SuperAdminOnly,
):
    """Get platform-level API keys (masked)."""
    settings = request.app.state.settings

    openai_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    gemini_key = getattr(settings, "GEMINI_API_KEY", "") or ""

    openai_info = None
    if openai_key:
        openai_info = PlatformKeyInfo(
            provider="openai",
            masked_key=admin_service.mask_key(openai_key),
            status="active",
        )

    gemini_info = None
    if gemini_key:
        gemini_info = PlatformKeyInfo(
            provider="gemini",
            masked_key=admin_service.mask_key(gemini_key),
            status="active",
        )

    return PlatformKeysResponse(openai=openai_info, gemini=gemini_info)


@router.post("/platform/rotate", response_model=RotateKeyResponse)
async def rotate_platform_key(
    body: RotateKeyRequest,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Rotate a platform API key. Updates DB audit log. Actual env var update requires Cloud Run redeploy."""
    masked = admin_service.mask_key(body.new_key)

    await admin_service.log_key_action(
        db,
        provider=body.provider,
        action="ROTATE",
        performed_by=current_user.get("user_id"),
        new_key_masked=masked,
        reason=body.reason,
    )

    return RotateKeyResponse(success=True, provider=body.provider, masked_key=masked)


@router.get("/tenants", response_model=PaginatedResponse[TenantKeyResponse])
async def list_tenant_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """List per-tenant LLM provider keys (paginated)."""
    offset = (page - 1) * page_size
    try:
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM llm_provider_keys")
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            text(
                "SELECT k.id, k.tenant_id, k.provider, k.api_key_encrypted, k.created_at, "
                "t.nombre AS tenant_nombre "
                "FROM llm_provider_keys k "
                "LEFT JOIN tenants t ON t.id = k.tenant_id "
                "ORDER BY k.created_at DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {"offset": offset, "limit": page_size},
        )
        rows = result.mappings().all()
    except Exception:
        return PaginatedResponse.build(items=[], total=0, page=page, page_size=page_size)

    items = [
        TenantKeyResponse(
            id=row["id"],
            tenant_id=row["tenant_id"],
            tenant_nombre=row["tenant_nombre"],
            provider=row["provider"],
            masked_key=admin_service.mask_key(row["api_key_encrypted"]) if row["api_key_encrypted"] else "****",
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)
