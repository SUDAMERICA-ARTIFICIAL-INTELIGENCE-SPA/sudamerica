"""Shared fixtures for tasks tests."""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
import pytest_asyncio
from app.config import TasksSettings
from httpx import ASGITransport, AsyncClient

TEST_SETTINGS = TasksSettings(
    DATABASE_URL="sqlite+aiosqlite:///./test_tasks.db",
    JWT_SECRET_KEY="test-secret-key-0123456789abcdef",
    INTERNAL_SERVICE_SECRET_KEY=os.environ["TASKS_INTERNAL_SERVICE_SECRET_KEY"],
    SMTP_HOST="localhost",
    SMTP_PORT=587,
    SMTP_USER="test@test.com",
    SMTP_PASSWORD="password",
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
OTHER_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture(scope="session")
def settings() -> TasksSettings:
    return TEST_SETTINGS


def _make_token(
    user_id: uuid.UUID = USER_ID,
    tenant_id: uuid.UUID = TENANT_ID,
    role: str = "ADMIN",
) -> str:
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "email": "test@sudamerica.ai",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, TEST_SETTINGS.JWT_SECRET_KEY, algorithm="HS256")


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_make_token()}",
        "X-Tenant-ID": str(TENANT_ID),
    }


@pytest_asyncio.fixture()
async def client(settings: TasksSettings) -> AsyncGenerator[AsyncClient, None]:
    with patch("app.config.TasksSettings", return_value=settings):
        from app.main import create_app

        from shared.database.dependencies import get_db

        app = create_app()
        app.state.settings = settings
        mock_db = AsyncMock(spec=True)

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


@pytest.fixture()
def mock_smtp() -> AsyncMock:
    return AsyncMock(return_value=(250, "OK"))
