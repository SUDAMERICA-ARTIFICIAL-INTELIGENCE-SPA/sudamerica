"""Tests for comanda customer notification (state changes + rating prompt)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.comanda_notify import (
    build_status_message,
    notify_customer_state_change,
    notify_order_ready,
)


class FakeSettings:
    INTERNAL_SERVICE_SECRET_KEY = "a" * 64
    JWT_ALGORITHM = "HS256"
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS = 300
    SERVICE_CANALES_URL = "http://localhost:8004"


@pytest.fixture
def settings():
    return FakeSettings()


def _mock_post_ok():
    resp = AsyncMock()
    resp.raise_for_status = lambda: None
    return AsyncMock(return_value=resp)


# ── build_status_message (pure function) ─────────────────────────────


class TestBuildStatusMessage:
    def test_en_cocina_includes_prep_time(self):
        msg = build_status_message(
            "EN_COCINA", "DELIVERY", uuid4(), "Juan", prep_time_min=25
        )
        assert msg is not None
        assert "cocina" in msg.lower()
        assert "25" in msg
        assert "Juan" in msg

    def test_listo_retiro_variant(self):
        msg = build_status_message("LISTO", "RETIRO", uuid4(), "Ana")
        assert msg is not None
        assert "retiro" in msg.lower()
        assert "Ana" in msg

    def test_listo_delivery_variant(self):
        msg = build_status_message("LISTO", "DELIVERY", uuid4(), "Luis")
        assert msg is not None
        assert "repartidor" in msg.lower()

    def test_listo_mesa_variant(self):
        msg = build_status_message("LISTO", "MESA", uuid4(), "Sofia")
        assert msg is not None
        assert "mesa" in msg.lower()

    def test_en_proceso_generic_sin_cocina(self):
        # Rubros sin cocina (FSM genérica): EN_PROCESO ahora notifica (antes se perdía
        # en silencio). Texto neutral, sin "cocina" ni 🍽️.
        msg = build_status_message("EN_PROCESO", "RETIRO", uuid4(), "Nora", prep_time_min=20)
        assert msg is not None
        assert "cocina" not in msg.lower()
        assert "🍽️" not in msg
        assert "20" in msg
        assert "Nora" in msg

    def test_en_ruta_generic(self):
        msg = build_status_message("EN_RUTA", "DELIVERY", uuid4(), "Pedro")
        assert msg is not None
        assert "camino" in msg.lower()

    def test_entregado_generic(self):
        msg = build_status_message("ENTREGADO", "RETIRO", uuid4(), "Lia")
        assert msg is not None
        assert "entregado" in msg.lower()

    def test_unknown_state_returns_none(self):
        assert (
            build_status_message("PENDIENTE", "MESA", uuid4(), "Juan") is None
        )

    def test_no_nombre_uses_default(self):
        msg = build_status_message("EN_COCINA", "DELIVERY", uuid4(), None)
        assert msg is not None
        assert "cliente" in msg.lower()


# ── notify_customer_state_change (HTTP side-effects) ─────────────────


@pytest.mark.asyncio
async def test_notify_en_cocina_sends_one_message(settings):
    tenant_id = uuid4()
    comanda_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "Juan",
            "DELIVERY", "EN_COCINA", prep_time_min=30,
        )

    assert post.await_count == 1
    body = post.call_args.kwargs["json"]
    assert body["to"] == "56912345678"
    assert "cocina" in body["message"].lower()


@pytest.mark.asyncio
async def test_notify_listo_delivery(settings):
    tenant_id = uuid4()
    comanda_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "María",
            "DELIVERY", "LISTO",
        )

    assert post.await_count == 1
    body = post.call_args.kwargs["json"]
    assert "repartidor" in body["message"].lower()


@pytest.mark.asyncio
async def test_notify_entregado_sends_two_messages(settings):
    """ENTREGADO must send status + rating prompt as two separate messages."""
    tenant_id = uuid4()
    comanda_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "Ana",
            "RETIRO", "ENTREGADO",
        )

    assert post.await_count == 2
    first_body = post.call_args_list[0].kwargs["json"]
    second_body = post.call_args_list[1].kwargs["json"]
    assert "entregado" in first_body["message"].lower()
    assert "experiencia" in second_body["message"].lower()
    assert "⭐" in second_body["message"]


@pytest.mark.asyncio
async def test_notify_unknown_state_noop(settings):
    tenant_id = uuid4()
    comanda_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "Juan",
            "DELIVERY", "PENDIENTE",
        )

    post.assert_not_called()


@pytest.mark.asyncio
async def test_notify_http_error_does_not_raise(settings):
    """Fire-and-forget: HTTP failures are logged and swallowed."""
    import httpx

    tenant_id = uuid4()
    comanda_id = uuid4()
    failing_post = AsyncMock(side_effect=httpx.HTTPError("boom"))
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = failing_post
        # Should not raise
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "Juan",
            "DELIVERY", "EN_COCINA",
        )


@pytest.mark.asyncio
async def test_notify_entregado_rating_failure_does_not_raise(settings):
    """If the status send works but the rating prompt fails, don't raise."""
    import httpx

    tenant_id = uuid4()
    comanda_id = uuid4()
    ok_resp = AsyncMock()
    ok_resp.raise_for_status = lambda: None
    call_count = {"n": 0}

    async def post_side_effect(*_a, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ok_resp
        raise httpx.HTTPError("rating flaky")

    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = AsyncMock(side_effect=post_side_effect)
        await notify_customer_state_change(
            settings, tenant_id, comanda_id, "56912345678", "Juan",
            "RETIRO", "ENTREGADO",
        )
    assert call_count["n"] == 2


# ── Legacy wrapper (backwards compat) ────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_notify_order_ready_retiro(settings):
    tenant_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_order_ready(settings, tenant_id, "56912345678", "Juan", "RETIRO")

    assert post.await_count == 1
    body = post.call_args.kwargs["json"]
    assert "retiro" in body["message"].lower()


@pytest.mark.asyncio
async def test_legacy_notify_order_ready_mesa_skipped(settings):
    tenant_id = uuid4()
    post = _mock_post_ok()
    with patch("app.services.comanda_notify.internal_http") as http:
        http.post = post
        await notify_order_ready(settings, tenant_id, "56912345678", "Juan", "MESA")

    post.assert_not_called()
