"""Health check endpoints for canales_service."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.schemas.base import HealthResponse
from shared.utils.health import (
    build_health_report,
    check_database,
    check_evolution_api,
    check_service,
)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is alive."""
    return HealthResponse(service="canales_service")


@router.get("/health/ready")
async def readiness(request: Request):
    """Readiness probe — checks DB, peer services, and Evolution API."""
    settings = request.app.state.settings
    checks = [
        check_database(request.app.state.session_factory),
        check_service(settings.SERVICE_API_EXECUTE_URL, "api-execute"),
    ]
    if settings.EVOLUTION_API_URL:
        checks.append(
            check_evolution_api(settings.EVOLUTION_API_URL, settings.EVOLUTION_API_KEY)
        )
    report = await build_health_report(
        service_name="canales-service",
        checks=checks,
    )
    status_code = 200 if report.status != "unhealthy" else 503
    return JSONResponse(content=report.to_dict(), status_code=status_code)
