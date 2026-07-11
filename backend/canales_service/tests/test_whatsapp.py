"""Tests for WhatsApp routes."""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest
from app.routes import whatsapp as whatsapp_route
from pydantic import ValidationError

from .conftest import TENANT_ID, TEST_SETTINGS_WITH_TOKEN, build_canales_settings


@pytest.mark.asyncio
async def test_webhook_whatsapp_processes_message(client, mock_evolution_instance, webhook_headers):
    payload = {
        "instance": f"tenant-{TENANT_ID}",
        "data": {
            "key": {"remoteJid": "5491155551234@s.whatsapp.net"},
            "message": {"conversation": "Hola, necesito info"},
        },
    }
    mock_lead_resp = MagicMock()
    mock_lead_resp.status_code = 200
    mock_lead_resp.json.return_value = {"data": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}]}
    mock_lead_resp.raise_for_status = MagicMock(return_value=None)

    mock_ai_resp = MagicMock()
    mock_ai_resp.status_code = 200
    mock_ai_resp.json.return_value = {"response": "Hola!", "conversation_id": "abc"}
    mock_ai_resp.raise_for_status = MagicMock(return_value=None)

    mock_send_resp = MagicMock()
    mock_send_resp.status_code = 200
    mock_send_resp.json.return_value = {"key": {"id": "msg-456"}}
    mock_send_resp.raise_for_status = MagicMock(return_value=None)

    async def mock_post(self, path, **kwargs):
        if "/chat" in path:
            return mock_ai_resp
        if "/sendText" in path:
            return mock_send_resp
        return mock_lead_resp

    async def mock_get(self, path, **kwargs):
        return mock_lead_resp

    with (
        patch("app.services.whatsapp_service.HttpClient.post", mock_post),
        patch("app.services.whatsapp_service.HttpClient.get", mock_get),
        patch("app.routes.whatsapp.set_instance_lookup_context", new_callable=AsyncMock) as mock_lookup_ctx,
        patch(
            "app.services.whatsapp_service.instance_service.lookup_by_instance_name",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        response = await client.post(
            "/api/v1/canales/webhook/whatsapp",
            json=payload,
            headers=webhook_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    mock_lookup_ctx.assert_awaited_once_with(ANY, f"tenant-{TENANT_ID}")


@pytest.mark.asyncio
async def test_webhook_connection_update_connected(client, webhook_headers):
    payload = {
        "event": "connection.update",
        "instance": f"tenant-{TENANT_ID}",
        "data": {"state": "open"},
    }
    with patch(
        "app.routes.whatsapp.instance_service.update_status",
        AsyncMock(return_value=MagicMock()),
    ), patch(
        "app.routes.whatsapp.set_instance_lookup_context",
        new_callable=AsyncMock,
    ) as mock_lookup_ctx:
        response = await client.post(
            "/api/v1/canales/webhook/whatsapp",
            json=payload,
            headers=webhook_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connection_updated"
    assert data["state"] == "CONNECTED"
    mock_lookup_ctx.assert_awaited_once_with(ANY, f"tenant-{TENANT_ID}")


@pytest.mark.asyncio
async def test_send_whatsapp_success(
    client,
    auth_headers,
    mock_evolution_send,
    mock_evolution_instance,
):
    body = {
        "to": "5491155551234",
        "message": "Hola desde Sudamérica AI",
        "tenant_id": str(TENANT_ID),
    }
    with (
        patch("app.services.whatsapp_service.HttpClient.post", return_value=mock_evolution_send),
        patch(
            "app.routes.whatsapp.instance_service.get_instance_for_tenant",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
    ):
        response = await client.post(
            "/api/v1/canales/whatsapp/send",
            json=body,
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message_id"] == "msg-123"


@pytest.mark.asyncio
async def test_send_whatsapp_cross_tenant_forbidden(client, other_tenant_auth_headers):
    body = {
        "to": "5491155551234",
        "message": "Hola",
        "tenant_id": str(TENANT_ID),
    }
    response = await client.post(
        "/api/v1/canales/whatsapp/send",
        json=body,
        headers=other_tenant_auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_configure_instance_settings_success(client, auth_headers, mock_evolution_instance):
    tenant_id = str(TENANT_ID)
    body = {
        "reject_call": True,
        "always_online": True,
        "read_messages": True,
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok"}
    mock_resp.raise_for_status = MagicMock(return_value=None)

    with (
        patch("app.services.qr_service.HttpClient.post", return_value=mock_resp),
        patch(
            "app.routes.whatsapp.instance_service.get_instance_for_tenant",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
    ):
        response = await client.post(
            f"/api/v1/canales/whatsapp/instance/{tenant_id}/settings",
            json=body,
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["instance_name"] == f"tenant-{tenant_id}"


def _make_json_response(status_code, json_value):
    """Build a MagicMock HTTP response with status, json, and raise_for_status."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock(return_value=None)
    resp.json.return_value = json_value
    return resp


def _build_sync_history_mocks():
    """Build all mock responses needed for the sync history test."""
    lead_resp = _make_json_response(200, {
        "data": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}],
    })
    chats_resp = _make_json_response(200, [
        {"remoteJid": "5491155551234@s.whatsapp.net"},
        {"remoteJid": "120363333333@g.us"},
    ])
    messages_resp = _make_json_response(200, {
        "messages": {
            "total": 2, "pages": 1, "currentPage": 1,
            "records": [
                {
                    "key": {"remoteJid": "5491155551234@s.whatsapp.net", "fromMe": False},
                    "message": {"conversation": "Hola, te escribi antes de conectar"},
                    "messageTimestamp": 1700000000,
                },
                {
                    "key": {"remoteJid": "5491155551234@s.whatsapp.net", "fromMe": True},
                    "message": {"extendedTextMessage": {"text": "Claro, ya vi tu chat"}},
                    "messageTimestamp": 1700000060,
                },
            ],
        },
    })
    import_resp = _make_json_response(200, {
        "lead_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "imported_count": 2, "skipped_count": 0,
    })
    return lead_resp, chats_resp, messages_resp, import_resp


def _build_sync_history_route_mocks(lead_resp, chats_resp, messages_resp, import_resp):
    """Return mock_post and mock_get callables that route by path."""
    async def mock_post(self, path, **kwargs):
        if path.startswith("/chat/findChats/"):
            return chats_resp
        if path.startswith("/chat/findMessages/"):
            return messages_resp
        if path.endswith("/api/v1/ai/conversations/import"):
            return import_resp
        raise AssertionError(f"Unexpected POST path: {path}")

    async def mock_get(self, path, **kwargs):
        if "/api/v1/core/leads" in path:
            return lead_resp
        raise AssertionError(f"Unexpected GET path: {path}")

    return mock_post, mock_get


def _assert_sync_history_success(response):
    """Assert the sync history response has expected success values."""
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["chats_scanned"] == 1
    assert data["chats_imported"] == 1
    assert data["messages_imported"] == 2
    assert data["messages_skipped"] == 0


@pytest.mark.asyncio
async def test_sync_whatsapp_history_success(client, auth_headers, mock_evolution_instance):
    tenant_id = str(TENANT_ID)
    lead_resp, chats_resp, msgs_resp, import_resp = _build_sync_history_mocks()
    mock_post, mock_get = _build_sync_history_route_mocks(
        lead_resp, chats_resp, msgs_resp, import_resp,
    )

    with (
        patch("app.services.whatsapp_service.HttpClient.post", mock_post),
        patch("app.services.whatsapp_service.HttpClient.get", mock_get),
        patch(
            "app.routes.whatsapp.instance_service.get_instance_for_tenant",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
    ):
        response = await client.post(
            f"/api/v1/canales/whatsapp/instance/{tenant_id}/history/sync",
            json={"page_size": 100},
            headers=auth_headers,
        )

    _assert_sync_history_success(response)


@pytest.mark.asyncio
async def test_sync_whatsapp_history_cross_tenant_forbidden(client, other_tenant_auth_headers):
    response = await client.post(
        f"/api/v1/canales/whatsapp/instance/{TENANT_ID}/history/sync",
        headers=other_tenant_auth_headers,
    )

    assert response.status_code == 403


def test_parse_evolution_payload_supports_plain_string_message():
    payload = {
        "instance": f"tenant-{TENANT_ID}",
        "data": {
            "key": {
                "remoteJid": "5491155551234@s.whatsapp.net",
                "fromMe": False,
            },
            "message": "Hola desde WhatsApp",
        },
    }

    incoming = whatsapp_route._parse_evolution_payload(payload)

    assert incoming is not None
    assert incoming.message == "Hola desde WhatsApp"


def test_parse_evolution_payload_passes_outbound_messages_with_flag():
    payload = {
        "instance": f"tenant-{TENANT_ID}",
        "data": {
            "key": {
                "remoteJid": "5491155551234@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {"conversation": "Mensaje saliente"},
        },
    }

    result = whatsapp_route._parse_evolution_payload(payload)
    assert result is not None
    assert result.from_me is True
    assert result.message == "Mensaje saliente"
    assert result.sender == "5491155551234@s.whatsapp.net"


def test_parse_evolution_payload_reads_image_caption():
    payload = {
        "instance": f"tenant-{TENANT_ID}",
        "data": {
            "key": {
                "remoteJid": "5491155551234@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {
                "imageMessage": {
                    "caption": "Necesito información de precios",
                }
            },
        },
    }

    incoming = whatsapp_route._parse_evolution_payload(payload)

    assert incoming is not None
    assert incoming.message == "Necesito información de precios"


# --- Webhook token validation ---


def test_webhook_configuration_requires_token():
    with pytest.raises(ValidationError, match="WEBHOOK_TOKEN must be configured"):
        build_canales_settings(webhook_token="")


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _MappingsResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        return _SessionContext(self._sessions.pop(0))


@pytest.mark.asyncio
async def test_resolve_tenant_from_instance_name_projects_only_tenant_id():
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(TENANT_ID)

    with patch(
        "app.routes.whatsapp.set_instance_lookup_context",
        new_callable=AsyncMock,
    ) as mock_lookup_ctx:
        tenant_id = await whatsapp_route._resolve_tenant_from_instance_name(
            db,
            f"tenant-{TENANT_ID}",
        )

    query = str(db.execute.await_args.args[0])
    params = db.execute.await_args.args[1]

    assert tenant_id == TENANT_ID
    mock_lookup_ctx.assert_awaited_once_with(db, f"tenant-{TENANT_ID}")
    assert "SELECT tenant_id" in query
    assert "SELECT *" not in query.upper()
    assert params == {"instance_name": f"tenant-{TENANT_ID}"}


@pytest.mark.asyncio
async def test_handle_group_message_sets_tenant_context_for_tenant_scoped_queries():
    session_lookup = AsyncMock()
    session_lookup.execute.side_effect = [
        _ScalarResult(TENANT_ID),
        _MappingsResult({"tenant_id": TENANT_ID, "sucursal_nombre": "Centro"}),
    ]
    session_driver = AsyncMock()
    session_driver.execute.return_value = _ScalarResult("Carlos")
    session_pending = AsyncMock()
    comanda_id = uuid.uuid4()
    session_pending.execute.return_value = _ScalarResult(comanda_id)

    request = MagicMock()
    request.app.state.settings = build_canales_settings()
    request.app.state.session_factory = _SessionFactory(
        [session_lookup, session_driver, session_pending]
    )
    incoming = whatsapp_route.WhatsAppIncoming(
        sender="120363040123456789@g.us",
        message="TOMO",
        instance_name=f"tenant-{TENANT_ID}",
    )
    raw_data = {
        "_group_jid": "120363040123456789@g.us",
        "_participant_jid": "56912345678@s.whatsapp.net",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = MagicMock(status_code=200, text="ok")
    mock_http_cm = MagicMock()
    mock_http_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.routes.whatsapp.set_instance_lookup_context",
            new_callable=AsyncMock,
        ) as mock_lookup_ctx,
        patch(
            "app.routes.whatsapp.set_tenant_context",
            new_callable=AsyncMock,
        ) as mock_tenant_ctx,
        patch(
            "app.routes.whatsapp.whatsapp_service._service_headers",
            return_value={"Authorization": "Bearer svc"},
        ),
        patch(
            "app.routes.whatsapp.whatsapp_service.send_message",
            new_callable=AsyncMock,
        ),
        patch("httpx.AsyncClient", return_value=mock_http_cm),
    ):
        result = await whatsapp_route._handle_group_message(raw_data, incoming, request)

    assert result == {"status": "claimed", "comanda_id": str(comanda_id)}
    mock_lookup_ctx.assert_awaited_once_with(session_lookup, f"tenant-{TENANT_ID}")
    mock_tenant_ctx.assert_has_awaits(
        [
            call(session_lookup, str(TENANT_ID)),
            call(session_driver, str(TENANT_ID)),
            call(session_pending, str(TENANT_ID)),
        ]
    )


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_token(settings):
    """Webhook must return 401 when WEBHOOK_TOKEN is set and request lacks valid token."""
    from app.main import create_app
    from shared.database.dependencies import get_db
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    app.state.settings = TEST_SETTINGS_WITH_TOKEN
    mock_db = AsyncMock(spec=True)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        payload = {
            "event": "connection.update",
            "instance": f"tenant-{TENANT_ID}",
            "data": {"state": "open"},
        }
        response = await ac.post("/api/v1/canales/webhook/whatsapp", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_accepts_valid_token(settings):
    """Webhook accepts requests with valid apikey header when WEBHOOK_TOKEN is set."""
    from app.main import create_app
    from shared.database.dependencies import get_db
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    app.state.settings = TEST_SETTINGS_WITH_TOKEN
    mock_db = AsyncMock(spec=True)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        payload = {
            "event": "connection.update",
            "instance": f"tenant-{TENANT_ID}",
            "data": {"state": "open"},
        }
        with patch(
            "app.routes.whatsapp.instance_service.update_status",
            AsyncMock(return_value=MagicMock()),
        ):
            response = await ac.post(
                "/api/v1/canales/webhook/whatsapp",
                json=payload,
                headers={"apikey": TEST_SETTINGS_WITH_TOKEN.WEBHOOK_TOKEN},
            )
    assert response.status_code == 200


# --- Human reply endpoint ---


@pytest.mark.asyncio
async def test_reply_to_prospect_success(
    client,
    auth_headers,
    mock_evolution_instance,
    mock_evolution_send,
):
    """Human agent can send a reply that gets sent and persisted."""
    body = {
        "lead_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "message": "Hola, soy tu asesor",
    }

    mock_lead_resp = MagicMock()
    mock_lead_resp.status_code = 200
    mock_lead_resp.json.return_value = {
        "data": {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "telefono": "5491155551234",
        }
    }
    mock_lead_resp.raise_for_status = MagicMock(return_value=None)

    mock_import_resp = MagicMock()
    mock_import_resp.status_code = 200
    mock_import_resp.raise_for_status = MagicMock(return_value=None)
    mock_import_resp.json.return_value = {"imported_count": 1, "skipped_count": 0}

    async def mock_get(self, path, **kwargs):
        return mock_lead_resp

    async def mock_post(self, path, **kwargs):
        if "/sendText" in path:
            return mock_evolution_send
        if "/conversations/import" in path:
            return mock_import_resp
        raise AssertionError(f"Unexpected POST path: {path}")

    with (
        patch("app.services.whatsapp_service.HttpClient.get", mock_get),
        patch("app.services.whatsapp_service.HttpClient.post", mock_post),
        patch(
            "app.routes.whatsapp.instance_service.get_instance_for_tenant",
            new_callable=AsyncMock,
            return_value=mock_evolution_instance,
        ),
    ):
        response = await client.post(
            "/api/v1/canales/whatsapp/reply",
            json=body,
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["lead_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
