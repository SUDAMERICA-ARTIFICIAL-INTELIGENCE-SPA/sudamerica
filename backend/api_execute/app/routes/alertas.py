"""SmartAlert routes: GET list (paginated + filters), PATCH mark read."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.schemas import PaginationParams

from app.schemas.smart_alert import SmartAlertResponse, SmartAlertUpdate
from app.services import smart_alert_svc

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("")
async def list_alerts(
    pagination: PaginationParams = Depends(),
    tipo: str | None = Query(None, description="Filter by alert type"),
    leido: bool | None = Query(None, description="Filter by read status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List smart alerts for the current tenant."""
    return await smart_alert_svc.list_alerts(
        db, current_user["tenant_id"], pagination, tipo=tipo, leido=leido
    )


@router.patch("/{alert_id}", response_model=SmartAlertResponse)
async def update_alert(
    alert_id: UUID,
    body: SmartAlertUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an alert (e.g., mark as read)."""
    data = body.model_dump(exclude_unset=True)
    return await smart_alert_svc.update_alert(
        db, current_user["tenant_id"], alert_id, data
    )
