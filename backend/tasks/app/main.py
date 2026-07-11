"""App factory for tasks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import TasksSettings
from app.routes import email, health, send_response, webhook_processor
from shared.database import create_engine, create_session_factory
from shared.middleware.request_id import RequestIdMiddleware
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.middleware.tenant import TenantMiddleware
from shared.utils import add_frontend_cors
from shared.utils.exceptions import register_exception_handlers
from shared.utils.logging import get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = TasksSettings()
    logger = get_logger("tasks", settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="Sudamérica AI Tasks", version="0.1.0", lifespan=lifespan)
    _configure_cors(app, settings)
    _configure_state(app, settings)
    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="tasks", logger=logger)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(email.router, prefix="/api/v1/tasks")
    app.include_router(send_response.router, prefix="/api/v1/tasks")
    app.include_router(webhook_processor.router, prefix="/api/v1/tasks")
    return app


def _configure_cors(app: FastAPI, settings: TasksSettings) -> None:
    add_frontend_cors(app, settings.FRONTEND_URL)


def _configure_state(app: FastAPI, settings: TasksSettings) -> None:
    engine = create_engine(settings.DATABASE_URL)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.jwt_secret_key = settings.JWT_SECRET_KEY
    app.state.jwt_algorithm = settings.JWT_ALGORITHM
    app.state.internal_service_signing_key = settings.INTERNAL_SERVICE_SECRET_KEY
    app.state.internal_service_trusted_keys = settings.internal_service_trusted_keys
    app.state.service_name = "tasks"
    app.state.settings = settings


app = create_app()
