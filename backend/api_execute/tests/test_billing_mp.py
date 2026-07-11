"""Tests for Mercado Pago billing: checkout, webhook signature/idempotency, plan sync."""

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant

from .conftest import TENANT_ID, TestSessionFactory

MP_SECRET = "test-mp-webhook-secret"


def _mp_signature(data_id: str, request_id: str, ts: str = "1718000000") -> str:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(MP_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


def _configure_mp(app) -> None:
    app.state.settings.PAYMENT_PROVIDER = "mercadopago"
    app.state.settings.MP_ACCESS_TOKEN = "test-mp-access-token"
    app.state.settings.MP_WEBHOOK_SECRET = MP_SECRET


@pytest.mark.asyncio
async def test_create_checkout_mercadopago(client, auth_headers, app):
    """Checkout returns the MP init_point with the configured CLP amount."""
    _configure_mp(app)

    captured: dict = {}

    async def fake_create_preapproval(body, settings):
        captured.update(body)
        return {"id": "preapproval_test_1", "init_point": "https://www.mercadopago.cl/subscriptions/checkout?preapproval_id=preapproval_test_1"}

    with patch(
        "app.services.mercadopago_service._create_preapproval",
        new=AsyncMock(side_effect=fake_create_preapproval),
    ):
        resp = await client.post(
            "/api/v1/core/billing/create-checkout",
            headers=auth_headers,
            json={"plan": "PLUS"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mercadopago"
    assert body["target_plan"] == "PLUS"
    assert "mercadopago" in body["checkout_url"]
    assert captured["auto_recurring"]["transaction_amount"] == 29990
    assert captured["auto_recurring"]["currency_id"] == "CLP"
    assert captured["external_reference"] == f"{TENANT_ID}|PLUS"
    assert captured["payer_email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_webhook_authorized_upgrades_and_is_idempotent(client, app):
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    request_id = "req-test-1"
    notification = {
        "id": 990001,
        "type": "subscription_preapproval",
        "action": "updated",
        "data": {"id": preapproval_id},
    }
    fake_preapproval = {
        "id": preapproval_id,
        "status": "authorized",
        "external_reference": f"{TENANT_ID}|PRO",
    }

    url = f"/api/v1/core/billing/webhook/mercadopago?data.id={preapproval_id}"
    headers = {
        "x-signature": _mp_signature(preapproval_id, request_id),
        "x-request-id": request_id,
        "Content-Type": "application/json",
    }

    with patch(
        "app.services.mercadopago_service._fetch_preapproval",
        new=AsyncMock(return_value=fake_preapproval),
    ):
        resp1 = await client.post(url, content=json.dumps(notification).encode(), headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        resp2 = await client.post(url, content=json.dumps(notification).encode(), headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_processed"

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "PRO"
        assert tenant.max_users == 20
        assert tenant.stripe_subscription_id == preapproval_id


@pytest.mark.asyncio
async def test_webhook_cancelled_downgrades_to_estandar(client, app):
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        tenant.plan = "PRO"
        tenant.max_users = 20
        tenant.max_leads_mes = 999_999
        tenant.stripe_subscription_id = preapproval_id
        await session.commit()

    request_id = "req-test-2"
    notification = {
        "id": 990002,
        "type": "subscription_preapproval",
        "action": "updated",
        "data": {"id": preapproval_id},
    }
    fake_preapproval = {
        "id": preapproval_id,
        "status": "cancelled",
        "external_reference": f"{TENANT_ID}|PRO",
    }

    with patch(
        "app.services.mercadopago_service._fetch_preapproval",
        new=AsyncMock(return_value=fake_preapproval),
    ):
        resp = await client.post(
            f"/api/v1/core/billing/webhook/mercadopago?data.id={preapproval_id}",
            content=json.dumps(notification).encode(),
            headers={
                "x-signature": _mp_signature(preapproval_id, request_id),
                "x-request-id": request_id,
                "Content-Type": "application/json",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "ESTANDAR"
        assert tenant.max_users == 3
        assert tenant.max_leads_mes == 100
        assert tenant.stripe_subscription_id is None


async def _post_preapproval_webhook(client, preapproval_id, notification_id, fake_preapproval):
    request_id = f"req-{notification_id}"
    notification = {
        "id": notification_id,
        "type": "subscription_preapproval",
        "action": "updated",
        "data": {"id": preapproval_id},
    }
    with patch(
        "app.services.mercadopago_service._fetch_preapproval",
        new=AsyncMock(return_value=fake_preapproval),
    ):
        return await client.post(
            f"/api/v1/core/billing/webhook/mercadopago?data.id={preapproval_id}",
            content=json.dumps(notification).encode(),
            headers={
                "x-signature": _mp_signature(preapproval_id, request_id),
                "x-request-id": request_id,
                "Content-Type": "application/json",
            },
        )


async def _set_tenant_plan(plan: str, max_users: int, max_leads: int, preapproval_id: str, config=None):
    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        tenant.plan = plan
        tenant.max_users = max_users
        tenant.max_leads_mes = max_leads
        tenant.stripe_subscription_id = preapproval_id
        if config is not None:
            tenant.config = config
        await session.commit()


@pytest.mark.asyncio
async def test_webhook_paused_starts_grace_period_without_downgrade(client, app):
    """First paused notification keeps the plan and records grace_until."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan("PRO", 20, 999_999, preapproval_id)

    resp = await _post_preapproval_webhook(
        client, preapproval_id, 990010,
        {"id": preapproval_id, "status": "paused", "external_reference": f"{TENANT_ID}|PRO"},
    )
    assert resp.status_code == 200

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "PRO"
        assert tenant.config["billing"]["grace_until"]


@pytest.mark.asyncio
async def test_webhook_paused_after_expired_grace_downgrades(client, app):
    """A paused notification after grace expiry downgrades to ESTANDAR."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan(
        "PRO", 20, 999_999, preapproval_id,
        config={"billing": {"grace_until": "2020-01-01T00:00:00+00:00"}},
    )

    resp = await _post_preapproval_webhook(
        client, preapproval_id, 990011,
        {"id": preapproval_id, "status": "paused", "external_reference": f"{TENANT_ID}|PRO"},
    )
    assert resp.status_code == 200

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "ESTANDAR"
        assert tenant.max_users == 3
        assert tenant.stripe_subscription_id is None
        assert "grace_until" not in tenant.config.get("billing", {})


@pytest.mark.asyncio
async def test_webhook_authorized_clears_grace_period(client, app):
    """A recovered (authorized) subscription clears any pending grace period."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan(
        "PRO", 20, 999_999, preapproval_id,
        config={"billing": {"grace_until": "2099-01-01T00:00:00+00:00"}},
    )

    resp = await _post_preapproval_webhook(
        client, preapproval_id, 990012,
        {"id": preapproval_id, "status": "authorized", "external_reference": f"{TENANT_ID}|PRO"},
    )
    assert resp.status_code == 200

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "PRO"
        assert "grace_until" not in tenant.config.get("billing", {})


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client, app):
    _configure_mp(app)

    notification = {
        "id": 990003,
        "type": "subscription_preapproval",
        "data": {"id": "preapproval_bad"},
    }
    resp = await client.post(
        "/api/v1/core/billing/webhook/mercadopago?data.id=preapproval_bad",
        content=json.dumps(notification).encode(),
        headers={
            "x-signature": "ts=1718000000,v1=deadbeef",
            "x-request-id": "req-bad",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_billing_usage_returns_consumption_vs_quota(client, auth_headers, app):
    _configure_mp(app)

    resp = await client.get("/api/v1/core/billing/usage", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"]
    assert body["leads_used"] >= 0
    assert body["leads_limit"] > 0
    assert body["users_used"] >= 1  # at least the admin user
    assert body["users_limit"] > 0
    assert isinstance(body["subscription_active"], bool)


@pytest.mark.asyncio
async def test_webhook_duplicate_event_key_returns_already_processed(client, app):
    """A pre-existing event row (race winner) short-circuits without a 500."""
    _configure_mp(app)
    from app.models.stripe_event import StripeEvent

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    notification_id = 990030
    event_key = f"mp_{notification_id}"  # handle_webhook derives this from payload id

    async with TestSessionFactory() as session:
        session.add(StripeEvent(
            stripe_event_id=event_key,
            event_type="mp.subscription_preapproval",
            payload={},
            processed=True,
        ))
        await session.commit()

    resp = await _post_preapproval_webhook(
        client, preapproval_id, notification_id,
        {"id": preapproval_id, "status": "authorized", "external_reference": f"{TENANT_ID}|PRO"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_webhook_paused_with_naive_grace_until_downgrades_without_error(client, app):
    """A tz-naive grace_until must not raise TypeError (fail-safe to downgrade)."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan(
        "PRO", 20, 999_999, preapproval_id,
        config={"billing": {"grace_until": "2020-01-01T00:00:00"}},  # no tz offset
    )

    resp = await _post_preapproval_webhook(
        client, preapproval_id, 990031,
        {"id": preapproval_id, "status": "paused", "external_reference": f"{TENANT_ID}|PRO"},
    )
    assert resp.status_code == 200

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "ESTANDAR"


@pytest.mark.asyncio
async def test_billing_usage_reports_inactive_during_grace(client, auth_headers, app):
    """A failing subscription in its grace window reports subscription_active=false."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan(
        "PRO", 20, 999_999, preapproval_id,
        config={"billing": {"grace_until": "2099-01-01T00:00:00+00:00"}},  # not yet expired
    )

    resp = await client.get("/api/v1/core/billing/usage", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["subscription_active"] is False
    assert body["grace_until"]
    assert body["plan"] == "PRO"  # future grace → not downgraded yet


@pytest.mark.asyncio
async def test_billing_usage_downgrades_on_expired_grace(client, auth_headers, app):
    """Opening /usage with an expired grace window lazily downgrades to ESTANDAR."""
    _configure_mp(app)

    preapproval_id = f"preapproval_{uuid.uuid4().hex[:12]}"
    await _set_tenant_plan(
        "PRO", 20, 999_999, preapproval_id,
        config={"billing": {"grace_until": "2020-01-01T00:00:00+00:00"}},  # expired
    )

    resp = await client.get("/api/v1/core/billing/usage", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "ESTANDAR"
    assert body["subscription_active"] is False

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "ESTANDAR"
        assert tenant.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_billing_usage_normalizes_deprecated_free_label(client, auth_headers, app):
    """A legacy plan='FREE' tenant is reported as ESTANDAR, never the deprecated label."""
    _configure_mp(app)

    await _set_tenant_plan("FREE", 3, 100, None, config={})

    resp = await client.get("/api/v1/core/billing/usage", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["plan"] == "ESTANDAR"


@pytest.mark.asyncio
async def test_create_checkout_dispatches_to_stripe_when_configured(client, auth_headers, app):
    """PAYMENT_PROVIDER=stripe keeps the legacy Stripe checkout working."""
    app.state.settings.PAYMENT_PROVIDER = "stripe"
    app.state.settings.STRIPE_PRICE_PRO = "price_test_pro"

    from unittest.mock import MagicMock

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test-session"

    with patch("stripe.checkout.Session.create", return_value=mock_session):
        resp = await client.post(
            "/api/v1/core/billing/create-checkout",
            headers=auth_headers,
            json={"plan": "PRO"},
        )

    assert resp.status_code == 200
    assert resp.json()["provider"] == "stripe"
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/test-session"
