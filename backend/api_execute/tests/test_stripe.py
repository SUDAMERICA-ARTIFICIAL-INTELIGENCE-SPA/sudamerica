"""Tests for stripe: checkout and webhook idempotency."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from .conftest import TENANT_ID, TestSessionFactory

@pytest.mark.asyncio
async def test_create_checkout_session(client, auth_headers, app):
    """Test checkout session creation (mocked Stripe)."""
    # Ensure STRIPE_PRICE_PRO is set on settings so price lookup succeeds
    app.state.settings.STRIPE_PRICE_PRO = "price_test_pro"

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test-session"

    with patch("stripe.checkout.Session.create", return_value=mock_session):
        resp = await client.post(
            "/api/v1/core/stripe/create-checkout",
            headers=auth_headers,
            json={"plan": "PRO"},
        )
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/test-session"
    assert resp.json()["target_plan"] == "PRO"


@pytest.mark.asyncio
async def test_webhook_idempotency(client, auth_headers):
    """Test that duplicate webhook events are handled idempotently."""
    event_id = f"evt_{uuid.uuid4().hex[:24]}"
    fake_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": TENANT_ID, "plan": "PRO"},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        # First call: should process
        resp1 = await client.post(
            "/api/v1/core/stripe/webhook",
            content=json.dumps(fake_event).encode(),
            headers={
                "Stripe-Signature": "test_sig",
                "Content-Type": "application/json",
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        # Second call with same event: should be already_processed
        resp2 = await client.post(
            "/api/v1/core/stripe/webhook",
            content=json.dumps(fake_event).encode(),
            headers={
                "Stripe-Signature": "test_sig",
                "Content-Type": "application/json",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_processed"

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        assert tenant.plan == "PRO"
        assert tenant.stripe_customer_id == "cus_test"
        assert tenant.stripe_subscription_id == "sub_test"


@pytest.mark.asyncio
async def test_subscription_deleted_downgrades_to_estandar(client):
    event_id = f"evt_{uuid.uuid4().hex[:24]}"

    async with TestSessionFactory() as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        assert tenant is not None
        tenant.plan = "PRO"
        tenant.max_users = 20
        tenant.max_leads_mes = 999_999
        tenant.stripe_customer_id = "cus_existing"
        tenant.stripe_subscription_id = "sub_existing"
        await session.commit()

    fake_event = {
        "id": event_id,
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_existing",
                "customer": "cus_existing",
                "metadata": {"tenant_id": TENANT_ID, "plan": "PRO"},
            }
        },
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        resp = await client.post(
            "/api/v1/core/stripe/webhook",
            content=json.dumps(fake_event).encode(),
            headers={
                "Stripe-Signature": "test_sig",
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
        assert tenant.stripe_customer_id == "cus_existing"
        assert tenant.stripe_subscription_id is None
