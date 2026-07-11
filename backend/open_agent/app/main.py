"""App factory for open_agent — Copiloto Administrativo (port 8005).

Stateless AI brain: receives system prompt from api_execute, runs LLM
with admin tools, and returns the response. No direct DB access.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import OpenAgentSettings
from app.routes import agent, health
from shared.middleware.request_id import RequestIdMiddleware
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.middleware.tenant import TenantMiddleware
from shared.utils import add_frontend_cors
from shared.utils.exceptions import register_exception_handlers
from shared.utils.http_client import internal_http
from shared.utils.logging import get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = OpenAgentSettings()
    logger = get_logger("open_agent", settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # internal_http propagates X-Request-ID automatically
        app.state.http_client = internal_http
        yield

    app = FastAPI(
        title="Sudamérica AI Copiloto Administrativo",
        version="0.1.0",
        lifespan=lifespan,
    )

    add_frontend_cors(app, settings.FRONTEND_URL)

    app.state.jwt_secret_key = settings.JWT_SECRET_KEY
    app.state.jwt_algorithm = settings.JWT_ALGORITHM
    app.state.internal_service_signing_key = settings.INTERNAL_SERVICE_SECRET_KEY
    app.state.internal_service_trusted_keys = settings.internal_service_trusted_keys
    app.state.service_name = "open_agent"
    app.state.settings = settings

    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="open_agent", logger=logger)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(agent.router, prefix="/api/v1/agent")

    return app


app = create_app()
