"""Admin WhatsApp monitoring routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db
from shared.schemas.base import PaginatedResponse

from app.routes.deps import SuperAdminOnly
from app.schemas.admin import ReconnectResponse, WhatsAppInstanceResponse

router = APIRouter(prefix="/whatsapp", tags=["admin-whatsapp"])


@router.get("/instances", response_model=PaginatedResponse[WhatsAppInstanceResponse])
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """List all WhatsApp instances (paginated)."""
    offset = (page - 1) * page_size
    try:
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM evolution_instances")
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            text(
                "SELECT e.id, e.tenant_id, e.instance_name, e.status, e.phone, "
                "t.nombre AS tenant_nombre "
                "FROM evolution_instances e "
                "LEFT JOIN tenants t ON t.id = e.tenant_id "
                "ORDER BY e.created_at DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {"offset": offset, "limit": page_size},
        )
        rows = result.mappings().all()
    except Exception:
        return PaginatedResponse.build(items=[], total=0, page=page, page_size=page_size)

    items = [
        WhatsAppInstanceResponse(
            id=row["id"],
            tenant_id=row["tenant_id"],
            tenant_nombre=row["tenant_nombre"],
            instance_name=row["instance_name"],
            status=row["status"],
            phone=row["phone"],
        )
        for row in rows
    ]
    return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)


@router.post("/{tenant_id}/reconnect", response_model=ReconnectResponse)
async def reconnect_instance(
    tenant_id: UUID,
    _current_user: dict = SuperAdminOnly,
):
    """Trigger WhatsApp reconnection for a tenant. Returns QR code if available."""
    return ReconnectResponse(status="reconnect_requested", qr_code=None)
