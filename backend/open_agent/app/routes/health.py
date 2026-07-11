"""Health check endpoints for open_agent (stateless — no DB)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.utils.health import build_health_report, check_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Liveness probe — process is alive."""
    return {"status": "ok", "service": "open_agent"}


@router.get("/health/ready")
async def readiness(request: Request):
    """Readiness probe — checks downstream api-execute."""
    settings = request.app.state.settings
    report = await build_health_report(
        service_name="open-agent",
        checks=[
            check_service(settings.SERVICE_API_EXECUTE_URL, "api-execute"),
        ],
    )
    status_code = 200 if report.status != "unhealthy" else 503
    return JSONResponse(content=report.to_dict(), status_code=status_code)
