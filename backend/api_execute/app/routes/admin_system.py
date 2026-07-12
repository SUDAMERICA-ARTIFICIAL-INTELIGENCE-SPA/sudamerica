"""Admin system health and config routes."""

import logging
import time

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db

from app.models.platform_config import PlatformConfig
from app.routes.deps import SuperAdminOnly
from app.schemas.admin import (
    ConfigUpdateRequest,
    DataModelResponse,
    PlatformConfigResponse,
    ServiceHealth,
    SystemHealthResponse,
)
from app.services import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system"])


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    request: Request,
    _current_user: dict = SuperAdminOnly,
):
    """Check health of all services."""
    settings = request.app.state.settings
    services_to_check = [
        ("api-execute", "http://localhost:8000"),
        ("callback-manual", getattr(settings, "SERVICE_CALLBACK_URL", "http://localhost:8002")),
        ("tasks", getattr(settings, "SERVICE_TASKS_URL", "http://localhost:8003")),
        ("canales-service", getattr(settings, "SERVICE_CANALES_URL", "http://localhost:8004")),
        ("open-agent", getattr(settings, "SERVICE_OPEN_AGENT_URL", "http://localhost:8005")),
    ]

    results = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services_to_check:
            start = time.monotonic()
            try:
                resp = await client.get(f"{url}/health")
                latency = (time.monotonic() - start) * 1000
                results.append(ServiceHealth(
                    name=name,
                    url=url,
                    status="healthy" if resp.status_code == 200 else "unhealthy",
                    latency_ms=round(latency, 1),
                ))
            except Exception:
                results.append(ServiceHealth(
                    name=name, url=url, status="unreachable", latency_ms=None
                ))

    return SystemHealthResponse(services=results)


@router.get("/data-model", response_model=DataModelResponse)
async def data_model(
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Expose the current database schema for the admin panel."""
    return await admin_service.get_data_model_snapshot(db)


@router.patch("/config", response_model=PlatformConfigResponse)
async def update_config(
    body: ConfigUpdateRequest,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Update a platform config value."""
    return await admin_service.upsert_platform_config(
        db, body.key, body.value, current_user.get("user_id")
    )
