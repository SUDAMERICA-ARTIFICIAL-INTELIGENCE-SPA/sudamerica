"""Health check endpoints for tasks service."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.schemas.base import HealthResponse
from shared.utils.health import build_health_report, check_database, check_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is alive."""
    return HealthResponse(service="tasks")


@router.get("/health/ready")
async def readiness(request: Request):
    """Readiness probe — checks DB and downstream services."""
    settings = request.app.state.settings
    report = await build_health_report(
        service_name="tasks",
        checks=[
            check_database(request.app.state.session_factory),
            check_service(settings.SERVICE_CANALES_URL, "canales-service"),
        ],
    )
    status_code = 200 if report.status != "unhealthy" else 503
    return JSONResponse(content=report.to_dict(), status_code=status_code)
