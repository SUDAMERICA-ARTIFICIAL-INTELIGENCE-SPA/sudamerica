"""SalesTarget routes: GET list (paginated + filters), POST upsert."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.schemas import PaginationParams

from app.schemas.sales_target import SalesTargetCreate, SalesTargetResponse
from app.services import sales_target_svc

router = APIRouter(prefix="/sales-targets", tags=["sales-targets"])


@router.get("")
async def list_targets(
    pagination: PaginationParams = Depends(),
    asesor_id: str | None = Query(None, description="Filter by advisor"),
    periodo: str | None = Query(None, description="Filter by period (YYYY-MM)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sales targets for the current tenant."""
    return await sales_target_svc.list_targets(
        db, current_user["tenant_id"], pagination,
        asesor_id=asesor_id, periodo=periodo,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SalesTargetResponse)
async def upsert_target(
    body: SalesTargetCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a sales target (upsert by tenant+asesor+periodo)."""
    return await sales_target_svc.upsert_target(
        db, current_user["tenant_id"], body.model_dump()
    )
