"""App factory for canales_service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap import ensure_canales_schema
from app.config import CanalesSettings
# Import the models package so Sucursal + EvolutionInstance register in
# Base.metadata and composite FKs resolve. Then eagerly configure mappers
# so any unresolved FK fails at boot, not as a runtime 500.
import app.models  # noqa: F401
from sqlalchemy.orm import configure_mappers
configure_mappers()

from app.routes import health, media, qr, whatsapp
from shared.database import create_engine, create_session_factory
from shared.middleware.request_id import RequestIdMiddleware
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.middleware.tenant import TenantMiddleware
from shared.utils import add_frontend_cors
from shared.utils.exceptions import register_exception_handlers
from shared.utils.http_client import aclose_pooled_client
from shared.utils.logging import get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = CanalesSettings()
    logger = get_logger("canales_service", settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await ensure_canales_schema(app.state.engine)
        yield
        await aclose_pooled_client()
        await app.state.engine.dispose()

    app = FastAPI(
        title="Sudamérica AI Canales Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    _configure_cors(app, settings)
    _configure_state(app, settings)
    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="canales_service", logger=logger)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(whatsapp.router, prefix="/api/v1/canales")
    app.include_router(qr.router, prefix="/api/v1/canales")
    app.include_router(media.router, prefix="/api/v1/canales")
    return app


def _configure_cors(app: FastAPI, settings: CanalesSettings) -> None:
    add_frontend_cors(app, settings.FRONTEND_URL)


def _configure_state(app: FastAPI, settings: CanalesSettings) -> None:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.jwt_secret_key = settings.JWT_SECRET_KEY
    app.state.jwt_algorithm = settings.JWT_ALGORITHM
    app.state.internal_service_signing_key = settings.INTERNAL_SERVICE_SECRET_KEY
    app.state.internal_service_trusted_keys = settings.internal_service_trusted_keys
    app.state.service_name = "canales_service"
    app.state.settings = settings


app = create_app()
