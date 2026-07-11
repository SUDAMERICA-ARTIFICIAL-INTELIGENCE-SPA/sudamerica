"""Health check endpoints for callback_manual."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.schemas import HealthResponse
from shared.utils.health import build_health_report, check_database, check_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is alive."""
    return HealthResponse(service="callback_manual")


@router.get("/health/ready")
async def health_ready(request: Request):
    """Readiness probe — checks DB and downstream services."""
    settings = request.app.state.settings
    report = await build_health_report(
        service_name="callback-manual",
        checks=[
            check_database(request.app.state.session_factory),
            check_service(settings.SERVICE_TASKS_URL, "tasks"),
        ],
    )
    status_code = 200 if report.status != "unhealthy" else 503
    return JSONResponse(content=report.to_dict(), status_code=status_code)
