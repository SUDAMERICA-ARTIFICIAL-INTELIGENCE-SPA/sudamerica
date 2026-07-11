"""Stripe service: checkout session + webhook handling (idempotent)."""

import asyncio
import logging
import uuid
from collections.abc import Mapping

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enums import TenantPlan
from shared.utils.exceptions import ConflictError

from app.config import ApiExecuteSettings
from app.models.stripe_event import StripeEvent
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


def _normalize_plan(raw_plan: str | None) -> TenantPlan | None:
    if not raw_plan:
        return None
    if raw_plan == TenantPlan.FREE.value:
        return TenantPlan.ESTANDAR
    try:
        return TenantPlan(raw_plan)
    except ValueError:
        logger.warning("Unknown Stripe plan received: %s", raw_plan)
        return None


def _frontend_url(settings: ApiExecuteSettings) -> str:
    return settings.FRONTEND_URL.rstrip("/")


def _price_id_for_plan(
    plan: TenantPlan,
    settings: ApiExecuteSettings,
) -> str:
    mapping = {
        TenantPlan.PLUS: settings.STRIPE_PRICE_PLUS,
        TenantPlan.PRO: settings.STRIPE_PRICE_PRO,
    }
    price_id = mapping.get(plan, "")
    if not price_id:
        raise ConflictError(f"Stripe price not configured for plan {plan.value}")
    return price_id


def _extract_metadata(payload: Mapping[str, object] | None) -> dict[str, str]:
    if not isinstance(payload, Mapping):
        return {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    return {
        str(key): str(value)
        for key, value in metadata.items()
        if value is not None
    }


def _extract_plan(payload: Mapping[str, object] | None) -> TenantPlan | None:
    metadata = _extract_metadata(payload)
    if plan := _normalize_plan(metadata.get("plan")):
        return plan

    if not isinstance(payload, Mapping):
        return None

    details = payload.get("subscription_details")
    if isinstance(details, Mapping):
        return _normalize_plan(_extract_metadata(details).get("plan"))
    return None


def _extract_tenant_uuid(payload: Mapping[str, object] | None) -> uuid.UUID | None:
    metadata = _extract_metadata(payload)
    candidates = [
        metadata.get("tenant_id"),
        metadata.get("tenantId"),
    ]

    if isinstance(payload, Mapping):
        details = payload.get("subscription_details")
        if isinstance(details, Mapping):
            detail_meta = _extract_metadata(details)
            candidates.extend([
                detail_meta.get("tenant_id"),
                detail_meta.get("tenantId"),
            ])

        client_reference_id = payload.get("client_reference_id")
        if isinstance(client_reference_id, str):
            candidates.append(client_reference_id)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return uuid.UUID(candidate)
        except ValueError:
            logger.warning("Invalid tenant ID in Stripe payload: %s", candidate)
    return None


def _subscription_id_from_payload(payload: Mapping[str, object] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    subscription_id = payload.get("subscription")
    if isinstance(subscription_id, str) and subscription_id:
        return subscription_id
    payload_id = payload.get("id")
    if isinstance(payload_id, str) and payload_id.startswith("sub_"):
        return payload_id
    return None


def _customer_id_from_payload(payload: Mapping[str, object] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    customer_id = payload.get("customer")
    if isinstance(customer_id, str) and customer_id:
        return customer_id
    return None


async def _resolve_tenant(
    db: AsyncSession,
    payload: Mapping[str, object] | None,
) -> Tenant | None:
    tenant_uuid = _extract_tenant_uuid(payload)
    if tenant_uuid:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_uuid)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant

    subscription_id = _subscription_id_from_payload(payload)
    if subscription_id:
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant

    customer_id = _customer_id_from_payload(payload)
    if customer_id:
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    return None


def _apply_plan(
    tenant: Tenant,
    plan: TenantPlan,
    *,
    customer_id: str | None,
    subscription_id: str | None,
) -> None:
    tenant.plan = plan.value
    tenant.max_users = plan.max_users
    tenant.max_leads_mes = plan.max_leads_mes
    if customer_id:
        tenant.stripe_customer_id = customer_id
    if subscription_id is not None:
        tenant.stripe_subscription_id = subscription_id


def _validate_upgrade(current_plan: TenantPlan, requested_plan: TenantPlan) -> None:
    """Validate plan upgrade rules. Raises ConflictError on invalid transitions."""
    if current_plan == requested_plan:
        raise ConflictError(f"Tenant is already on plan {requested_plan.value}")
    if current_plan == TenantPlan.PRO:
        raise ConflictError("Current plan is already the highest tier")
    if current_plan == TenantPlan.PLUS and requested_plan != TenantPlan.PRO:
        raise ConflictError("PLUS tenants can only upgrade to PRO via Stripe")


async def create_checkout_session(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_plan: str,
    settings: ApiExecuteSettings,
) -> str:
    """Create a Stripe Checkout session for a paid plan upgrade."""
    from app.services.tenant_service import get_tenant
    tenant = await get_tenant(db, tenant_id)

    requested_plan = _normalize_plan(target_plan)
    if requested_plan is None or requested_plan == TenantPlan.ESTANDAR:
        raise ConflictError("Only paid plans can be purchased via Stripe")

    current_plan = _normalize_plan(tenant.plan) or TenantPlan.ESTANDAR
    _validate_upgrade(current_plan, requested_plan)

    price_id = _price_id_for_plan(requested_plan, settings)
    frontend_url = _frontend_url(settings)
    metadata = {"tenant_id": str(tenant.id), "plan": requested_plan.value}
    checkout_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{frontend_url}/billing?success=true&plan={requested_plan.value}",
        "cancel_url": f"{frontend_url}/billing?cancel=true&plan={requested_plan.value}",
        "client_reference_id": str(tenant.id),
        "allow_promotion_codes": True,
        "metadata": metadata,
        "subscription_data": {"metadata": metadata},
    }
    if tenant.stripe_customer_id:
        checkout_kwargs["customer"] = tenant.stripe_customer_id

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = await asyncio.to_thread(stripe.checkout.Session.create, **checkout_kwargs)
    except stripe.StripeError as exc:
        logger.error("Stripe checkout creation failed: %s", exc)
        raise ConflictError(f"Stripe error: {exc.user_message or str(exc)}")
    return session.url


async def handle_webhook(
    db: AsyncSession,
    payload: bytes,
    sig_header: str,
    settings: ApiExecuteSettings,
) -> dict:
    """Process Stripe webhook (idempotent via stripe_events)."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        event = await asyncio.to_thread(
            stripe.Webhook.construct_event,
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.SignatureVerificationError as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise ConflictError("Invalid Stripe webhook signature")

    existing = await db.execute(
        select(StripeEvent).where(StripeEvent.stripe_event_id == event["id"])
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    db_event = StripeEvent(
        stripe_event_id=event["id"],
        event_type=event["type"],
        payload=dict(event),
        processed=False,
    )
    db.add(db_event)

    if event["type"] == "checkout.session.completed":
        await _handle_checkout_completed(db, event)

    if event["type"] in {"customer.subscription.created", "customer.subscription.updated"}:
        await _handle_subscription_updated(db, event)

    if event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, event)

    db_event.processed = True
    await db.flush()
    return {"status": "processed"}


async def _handle_checkout_completed(db: AsyncSession, event: dict) -> None:
    """Upgrade tenant on successful checkout completion."""
    session_data = event["data"]["object"]
    tenant = await _resolve_tenant(db, session_data)
    plan = _extract_plan(session_data)
    if tenant is None or plan is None:
        return

    _apply_plan(
        tenant,
        plan,
        customer_id=_customer_id_from_payload(session_data),
        subscription_id=_subscription_id_from_payload(session_data),
    )


async def _handle_subscription_updated(db: AsyncSession, event: dict) -> None:
    """Sync tenant plan when Stripe emits subscription lifecycle events."""
    sub_data = event["data"]["object"]
    tenant = await _resolve_tenant(db, sub_data)
    if tenant is None:
        return

    plan = _extract_plan(sub_data)
    if plan is None:
        tenant.stripe_customer_id = _customer_id_from_payload(sub_data) or tenant.stripe_customer_id
        tenant.stripe_subscription_id = _subscription_id_from_payload(sub_data) or tenant.stripe_subscription_id
        return

    _apply_plan(
        tenant,
        plan,
        customer_id=_customer_id_from_payload(sub_data),
        subscription_id=_subscription_id_from_payload(sub_data),
    )


async def _handle_subscription_deleted(db: AsyncSession, event: dict) -> None:
    """Downgrade tenant to ESTANDAR on subscription cancellation."""
    sub_data = event["data"]["object"]
    tenant = await _resolve_tenant(db, sub_data)
    if tenant is None:
        return

    estandar = TenantPlan.ESTANDAR
    tenant.plan = estandar.value
    tenant.max_users = estandar.max_users
    tenant.max_leads_mes = estandar.max_leads_mes
    tenant.stripe_customer_id = _customer_id_from_payload(sub_data) or tenant.stripe_customer_id
    tenant.stripe_subscription_id = None
