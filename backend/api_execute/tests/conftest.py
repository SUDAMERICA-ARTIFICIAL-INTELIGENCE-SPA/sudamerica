"""Test fixtures: aiosqlite mock DB, test client, auth helpers."""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

# Force SQLite for tests BEFORE any app imports
JWT_SECRET = "test-secret-key-sudamerica-dev-2026"
INTERNAL_SERVICE_SECRET = os.environ.get(
    "API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY",
    "test-api-execute-secret-key-32bytes!!"
)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", JWT_SECRET)
os.environ.setdefault("API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY", INTERNAL_SERVICE_SECRET)
# Peer service keys (unique per service, required by trust map validator)
os.environ.setdefault("AI_DIALER_INTERNAL_SERVICE_SECRET_KEY", "test-ai-dialer-secret-key-32bytes!!")
os.environ.setdefault("CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY", "test-callback-manual-secret-32bytes!")
os.environ.setdefault("TASKS_INTERNAL_SERVICE_SECRET_KEY", "test-tasks-service-secret-key-32bytes!")
os.environ.setdefault("CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY", "test-canales-svc-secret-key-32bytes!!")
os.environ.setdefault("OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY", "test-open-agent-secret-key-32bytes!!!")

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from shared.models.base import Base

# ---------------------------------------------------------------------------
# In-memory SQLite engine (async via aiosqlite, StaticPool for data sharing)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Create tables before each test session
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    # Import all models so Base.metadata is populated
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test DB session that rolls back
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Override get_db to skip PostgreSQL RLS for SQLite tests
# ---------------------------------------------------------------------------
async def override_get_db():
    """Yield a test DB session (no RLS, auto-commit on success)."""
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# FastAPI test app with overridden DB dependency
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def app():
    from shared.database.dependencies import get_db, get_db_admin

    from app.main import create_app

    application = create_app()
    application.state.engine = engine
    application.state.session_factory = TestSessionFactory
    # Skip RLS (SET LOCAL not supported in SQLite)
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_db_admin] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def make_token(
    user_id: str = USER_ID,
    tenant_id: str = TENANT_ID,
    role: str = "ADMIN",
    email: str = "admin@test.com",
    token_type: str = "access",
    sucursal_id: str | None = None,
) -> str:
    """Create a JWT token for testing."""
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "exp": exp,
        "type": token_type,
    }
    if sucursal_id is not None:
        payload["sucursal_id"] = sucursal_id
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def auth_headers() -> dict:
    """Authorization headers with ADMIN token."""
    token = make_token()
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest_asyncio.fixture(autouse=True)
async def _seed_tenant():
    """Ensure a tenant row exists for TENANT_ID so lead limit checks pass."""
    from app.models.tenant import Tenant
    from app.models.usuario import Usuario

    tenant_uuid = uuid.UUID(TENANT_ID)
    user_uuid = uuid.UUID(USER_ID)
    async with TestSessionFactory() as session:
        from sqlalchemy import select

        existing = await session.scalar(
            select(Tenant).where(Tenant.id == tenant_uuid)
        )
        if existing:
            # Reset tenant state so tests don't leak side effects
            existing.plan = "ESTANDAR"
            existing.max_users = 3
            existing.max_leads_mes = 100
            existing.activo = True
        else:
            session.add(Tenant(
                id=tenant_uuid,
                nombre="Test Tenant",
                slug="test-tenant",
                plan="ESTANDAR",
                max_users=3,
                max_leads_mes=100,
            ))
        existing_user = await session.scalar(
            select(Usuario).where(Usuario.id == user_uuid)
        )
        if not existing_user:
            session.add(Usuario(
                id=user_uuid,
                tenant_id=tenant_uuid,
                email="seed-user@test.com",
                hashed_password="seeded-password-hash",
                nombre="Seed",
                apellido="User",
                role="ADMIN",
                email_verified=True,
            ))
        await session.commit()
    yield


@pytest.fixture
def asesor_headers() -> dict:
    """Authorization headers with ASESOR token."""
    token = make_token(role="ASESOR")
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }
