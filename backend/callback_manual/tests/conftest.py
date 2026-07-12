"""Shared test fixtures for callback_manual tests."""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import patch

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from shared.models.base import Base
from shared.models.tenant import Tenant
from shared.utils.internal_service_auth import build_internal_service_trust_map

# ---------------------------------------------------------------------------
# Minimal stub tables for FK resolution in SQLite tests
# ---------------------------------------------------------------------------


class TestLead(Base):
    """Minimal leads table so RevisionHumana FK resolves."""

    __tablename__ = "leads"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), default="test")


Lead = TestLead


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "test-secret-key-sudamerica-dev-2026"
JWT_ALGORITHM = "HS256"
INTERNAL_SERVICE_SECRET = os.environ["CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY"]

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
OPERADOR_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Database engine & session factory (aiosqlite in-memory)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def engine():
    eng = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import models so Base.metadata is populated
    import app.models  # noqa: F401

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture()
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture()
async def session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------
def make_token(
    user_id: uuid.UUID = USER_ID,
    tenant_id: uuid.UUID = TENANT_ID,
    role: str = "ADMIN",
) -> str:
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "email": "test@example.com",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {make_token()}",
        "X-Tenant-ID": str(TENANT_ID),
    }


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------
def _configure_mock_settings(mock_instance):
    """Apply all test settings to a mocked CallbackSettings instance."""
    mock_instance.DATABASE_URL = TEST_DB_URL
    mock_instance.JWT_SECRET_KEY = JWT_SECRET
    mock_instance.JWT_ALGORITHM = JWT_ALGORITHM
    mock_instance.OPENAI_API_KEY = "test-key"
    mock_instance.SERVICE_TASKS_URL = "http://localhost:8003"
    mock_instance.INTERNAL_SERVICE_SECRET_KEY = INTERNAL_SERVICE_SECRET
    mock_instance.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY = os.environ["API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY"]
    mock_instance.TASKS_INTERNAL_SERVICE_SECRET_KEY = os.environ["TASKS_INTERNAL_SERVICE_SECRET_KEY"]
    mock_instance.CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY = os.environ["CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY"]
    mock_instance.INTERNAL_SERVICE_TOKEN_TTL_SECONDS = 300
    mock_instance.internal_service_trusted_keys = build_internal_service_trust_map(
        service_name="callback_manual",
        signing_key=mock_instance.INTERNAL_SERVICE_SECRET_KEY,
        trusted_keys={
            "api_execute": mock_instance.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
            "tasks": mock_instance.TASKS_INTERNAL_SERVICE_SECRET_KEY,
            "canales_service": mock_instance.CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY,
        },
    )
    mock_instance.LOG_LEVEL = "DEBUG"


def _setup_app_state(app, engine, session_factory, get_db_override):
    """Wire engine, session factory, JWT config, and DB override into the app."""
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.jwt_secret_key = JWT_SECRET
    app.state.jwt_algorithm = JWT_ALGORITHM
    app.dependency_overrides[get_db_override] = _make_db_override(session_factory)


def _make_db_override(session_factory):
    """Create a get_db override that uses the test session factory."""
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    return override_get_db


@pytest_asyncio.fixture()
async def client(engine, session_factory) -> AsyncGenerator[AsyncClient, None]:
    from shared.database.dependencies import get_db

    with patch("app.config.CallbackSettings") as MockSettings:
        _configure_mock_settings(MockSettings.return_value)
        from app.main import create_app
        app = create_app()

    _setup_app_state(app, engine, session_factory, get_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
