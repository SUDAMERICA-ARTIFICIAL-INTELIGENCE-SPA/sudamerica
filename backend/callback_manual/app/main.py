"""App factory for callback_manual — Post-proceso / Revision Humana (port 8002)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import CallbackSettings
from app.routes import health, revision, transcription
from shared.database import create_engine, create_session_factory
from shared.middleware.request_id import RequestIdMiddleware
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.middleware.tenant import TenantMiddleware
from shared.utils import add_frontend_cors
from shared.utils.exceptions import register_exception_handlers
from shared.utils.logging import get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = CallbackSettings()
    logger = get_logger("callback_manual", settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await app.state.engine.dispose()

    app = FastAPI(
        title="Sudamérica AI Callback Manual",
        description="Post-proceso / Revision Humana service",
        version="0.1.0",
        lifespan=lifespan,
    )

    add_frontend_cors(app, settings.FRONTEND_URL)

    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.jwt_secret_key = settings.JWT_SECRET_KEY
    app.state.jwt_algorithm = settings.JWT_ALGORITHM
    app.state.internal_service_signing_key = settings.INTERNAL_SERVICE_SECRET_KEY
    app.state.internal_service_trusted_keys = settings.internal_service_trusted_keys
    app.state.service_name = "callback_manual"
    app.state.settings = settings

    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="callback_manual", logger=logger)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(revision.router, prefix="/api/v1/reviews")
    app.include_router(transcription.router, prefix="/api/v1")

    return app


app = create_app()
