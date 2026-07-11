"""Admin metrics routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db

from app.routes.deps import SuperAdminOnly
from app.schemas.admin import MetricsOverview, TimeseriesPoint, TopTenantItem
from app.services import admin_service

router = APIRouter(prefix="/metrics", tags=["admin-metrics"])


@router.get("/overview", response_model=MetricsOverview)
async def metrics_overview(
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Platform KPIs at a glance."""
    return await admin_service.get_metrics_overview(db)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
async def metrics_timeseries(
    days: int = Query(30, ge=1, le=90),
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Daily metrics for the last N days."""
    return await admin_service.get_metrics_timeseries(db, days)


@router.get("/top-tenants", response_model=list[TopTenantItem])
async def top_tenants(
    limit: int = Query(10, ge=1, le=50),
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Top tenants by usage."""
    return await admin_service.get_top_tenants(db, limit)
