"""Tests for the POST /api/v1/tasks/send-response endpoint."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from .conftest import TENANT_ID, TEST_SETTINGS, _make_token
from shared.middleware.auth import create_service_token
from shared.models.enums import RevisionDeliveryStatus


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_make_token()}",
        "X-Tenant-ID": str(TENANT_ID),
    }


@pytest_asyncio.fixture()
async def client():
    with patch("app.config.TasksSettings", return_value=TEST_SETTINGS):
        from app.main import create_app
        from shared.database.dependencies import get_db

        app = create_app()
        app.state.settings = TEST_SETTINGS
        mock_db = AsyncMock()

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


LEAD_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


@pytest.fixture(autouse=True)
def mock_revision_claim():
    with patch(
        "app.services.send_response_service._claim_revision_delivery",
        new_callable=AsyncMock,
    ):
        yield


def _service_headers(
    service_name: str,
    signing_key: str,
    *,
    scopes: tuple[str, ...] = ("tasks:send_response",),
) -> dict[str, str]:
    token = create_service_token(
        service_name=service_name,
        audience="tasks",
        tenant_id=TENANT_ID,
        signing_key=signing_key,
        algorithm=TEST_SETTINGS.JWT_ALGORITHM,
        scopes=scopes,
        expires_in_seconds=TEST_SETTINGS.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(TENANT_ID),
    }


def _service_headers_with_identity_mismatch() -> dict[str, str]:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "callback_manual",
            "sub": "api_execute",
            "aud": "tasks",
            "tenant_id": str(TENANT_ID),
            "type": "service",
            "role": "ADMIN",
            "scopes": ["tasks:send_response"],
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        TEST_SETTINGS.CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY,
        algorithm=TEST_SETTINGS.JWT_ALGORITHM,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(TENANT_ID),
    }


@pytest.fixture()
def service_headers() -> dict[str, str]:
    return _service_headers(
        "callback_manual",
        TEST_SETTINGS.CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY,
    )


class TestSendResponse:
    """Test suite for the send-response endpoint."""

    async def test_send_response_no_lead_id(self, client: AsyncClient, auth_headers):
        with patch(
            "app.services.send_response_service._log_task",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": None,
                    "respuesta": "Test response",
                },
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No lead_id" in (data.get("detail") or "")

    async def test_send_response_lead_not_found(self, client: AsyncClient, auth_headers):
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.send_response_service._log_task",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Test response",
                },
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in (data.get("detail") or "").lower()

    async def test_send_response_via_email(self, client: AsyncClient, auth_headers):
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "Test Lead",
                "email": "lead@test.com",
                "telefono": None,
                "canal": "WEB",
            },
        ), patch(
            "app.services.send_response_service.email_service.send_email",
            new_callable=AsyncMock,
            return_value={"success": True, "message_id": "msg-123"},
        ), patch(
            "app.services.send_response_service._log_task",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Hola, esta es la respuesta aprobada",
                },
                headers=auth_headers,
            )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["canal"] == "EMAIL"

    async def test_send_response_no_contact_info(self, client: AsyncClient, auth_headers):
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "Test Lead",
                "email": None,
                "telefono": None,
                "canal": "WEB",
            },
        ), patch(
            "app.services.send_response_service._log_task",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Respuesta sin destino",
                },
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "contact" in (data.get("detail") or "").lower()

    async def test_send_response_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/tasks/send-response",
            json={
                "revision_id": str(uuid.uuid4()),
                "lead_id": str(LEAD_ID),
                "respuesta": "Test",
            },
        )
        assert response.status_code in (401, 403)

    async def test_send_response_rejects_tenant_header_mismatch(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/tasks/send-response",
            json={
                "revision_id": str(uuid.uuid4()),
                "lead_id": str(LEAD_ID),
                "respuesta": "Test",
            },
            headers={
                "Authorization": f"Bearer {_make_token()}",
                "X-Tenant-ID": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 403

    async def test_send_response_rejects_service_token_signed_with_wrong_key(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/tasks/send-response",
            json={
                "revision_id": str(uuid.uuid4()),
                "lead_id": str(LEAD_ID),
                "respuesta": "Respuesta interna",
            },
            headers=_service_headers(
                "callback_manual",
                TEST_SETTINGS.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
            ),
        )
        assert response.status_code == 401

    async def test_send_response_rejects_service_token_identity_mismatch(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/tasks/send-response",
            json={
                "revision_id": str(uuid.uuid4()),
                "lead_id": str(LEAD_ID),
                "respuesta": "Respuesta interna",
            },
            headers=_service_headers_with_identity_mismatch(),
        )
        assert response.status_code == 401

    async def test_send_response_rejects_unauthorized_service_caller(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/tasks/send-response",
            json={
                "revision_id": str(uuid.uuid4()),
                "lead_id": str(LEAD_ID),
                "respuesta": "Respuesta interna",
            },
            headers=_service_headers(
                "api_execute",
                TEST_SETTINGS.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
            ),
        )
        assert response.status_code == 403

    async def test_send_response_accepts_callback_manual_service_token(
        self,
        client: AsyncClient,
        service_headers,
    ):
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "Test Lead",
                "email": "lead@test.com",
                "telefono": None,
                "canal": "WEB",
            },
        ), patch(
            "app.services.send_response_service.email_service.send_email",
            new_callable=AsyncMock,
            return_value={"success": True, "message_id": "msg-123"},
        ), patch(
            "app.services.send_response_service._log_task",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Respuesta interna",
                },
                headers=service_headers,
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_send_response_whatsapp_falls_back_to_email(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        mark_delivery = AsyncMock()
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "WhatsApp Lead",
                "email": "wa@test.com",
                "telefono": "+56912345678",
                "canal": "WHATSAPP",
            },
        ), patch(
            "app.services.send_response_service._send_via_whatsapp",
            new_callable=AsyncMock,
            return_value={"success": False, "canal": "WHATSAPP", "detail": "timeout"},
        ), patch(
            "app.services.send_response_service._send_via_email",
            new_callable=AsyncMock,
            return_value={"success": True, "canal": "EMAIL", "detail": "msg-123"},
        ), patch(
            "app.services.send_response_service._mark_revision_delivery",
            mark_delivery,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Mensaje WhatsApp",
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == {"success": True, "canal": "EMAIL", "detail": "msg-123"}
        assert mark_delivery.await_args_list[-1].args[3] == RevisionDeliveryStatus.SENT.value

    async def test_send_response_whatsapp_and_email_fail(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        mark_delivery = AsyncMock()
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "WhatsApp Lead",
                "email": "wa@test.com",
                "telefono": "+56912345678",
                "canal": "WHATSAPP",
            },
        ), patch(
            "app.services.send_response_service._send_via_whatsapp",
            new_callable=AsyncMock,
            return_value={"success": False, "canal": "WHATSAPP", "detail": "timeout"},
        ), patch(
            "app.services.send_response_service._send_via_email",
            new_callable=AsyncMock,
            return_value={"success": False, "canal": "EMAIL", "detail": "smtp failed"},
        ), patch(
            "app.services.send_response_service._mark_revision_delivery",
            mark_delivery,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Mensaje WhatsApp",
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == {"success": False, "canal": "EMAIL", "detail": "smtp failed"}
        assert mark_delivery.await_args_list[-1].args[3] == RevisionDeliveryStatus.FAILED.value

    async def test_send_response_whatsapp_without_email_fails(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        mark_delivery = AsyncMock()
        with patch(
            "app.services.send_response_service._fetch_lead",
            new_callable=AsyncMock,
            return_value={
                "nombre": "WhatsApp Lead",
                "email": None,
                "telefono": "+56912345678",
                "canal": "WHATSAPP",
            },
        ), patch(
            "app.services.send_response_service._send_via_whatsapp",
            new_callable=AsyncMock,
            return_value={"success": False, "canal": "WHATSAPP", "detail": "timeout"},
        ), patch(
            "app.services.send_response_service._mark_revision_delivery",
            mark_delivery,
        ):
            response = await client.post(
                "/api/v1/tasks/send-response",
                json={
                    "revision_id": str(uuid.uuid4()),
                    "lead_id": str(LEAD_ID),
                    "respuesta": "Mensaje WhatsApp",
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == {"success": False, "canal": "WHATSAPP", "detail": "timeout"}
        assert mark_delivery.await_args_list[-1].args[3] == RevisionDeliveryStatus.FAILED.value
