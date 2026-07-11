"""Shared fixtures for canales_service tests."""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import pytest_asyncio
from app.config import CanalesSettings
from httpx import ASGITransport, AsyncClient

def build_canales_settings(*, webhook_token: str = "test-webhook-secret-1234567890abcdef") -> CanalesSettings:
    return CanalesSettings(
        DATABASE_URL="sqlite+aiosqlite:///./test_canales.db",
        JWT_SECRET_KEY="test-secret-key-0123456789abcdef",
        INTERNAL_SERVICE_SECRET_KEY=os.environ["CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY"],
        EVOLUTION_API_URL="http://mock-evolution:8080",
        EVOLUTION_API_KEY="test-evo-key",
        EVOLUTION_WEBHOOK_URL="http://mock-canales:8004/api/v1/canales/webhook/whatsapp",
        SERVICE_AI_DIALER_URL="http://mock-ai-dialer:8001",
        SERVICE_API_EXECUTE_URL="http://mock-api-execute:8000",
        WEBHOOK_TOKEN=webhook_token,
    )


TEST_SETTINGS = build_canales_settings()
TEST_SETTINGS_WITH_TOKEN = TEST_SETTINGS

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
OTHER_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture(scope="session")
def settings() -> CanalesSettings:
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


@pytest.fixture()
def webhook_headers() -> dict[str, str]:
    return {"apikey": TEST_SETTINGS_WITH_TOKEN.WEBHOOK_TOKEN}


@pytest.fixture()
def other_tenant_auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_make_token(tenant_id=OTHER_TENANT_ID)}",
        "X-Tenant-ID": str(OTHER_TENANT_ID),
    }


@pytest_asyncio.fixture()
async def client(settings: CanalesSettings) -> AsyncGenerator[AsyncClient, None]:
    with patch("app.config.CanalesSettings", return_value=settings):
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
def mock_evolution_instance():
    instance = MagicMock()
    instance.id = uuid.uuid4()
    instance.tenant_id = TENANT_ID
    instance.instance_name = f"tenant-{TENANT_ID}"
    instance.status = "CONNECTED"
    instance.phone_number = None
    instance.activo = True
    return instance


@pytest.fixture()
def mock_evolution_send() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {"key": {"id": "msg-123"}}
    return mock_resp


@pytest.fixture()
def mock_evolution_create_instance() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {
        "instance": {"instanceName": "tenant-test"},
        "hash": "evo-token-abc123",
    }
    return mock_resp


@pytest.fixture()
def mock_evolution_status() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {"instance": {"state": "open"}}
    return mock_resp
