"""Mercado Pago service: monthly subscriptions (preapproval) + webhook handling.

Subscriptions flow:
- create_subscription_checkout() POSTs /preapproval (auto_recurring monthly, CLP)
  and returns init_point — the frontend redirects there so the payer authorizes
  the recurring charge inside Mercado Pago.
- handle_webhook() processes `subscription_preapproval` notifications: it
  re-fetches the preapproval from the MP API (never trusts the notification
  body) and applies the plan upgrade/downgrade.

Storage notes (zero-migration design):
- Webhook idempotency reuses the stripe_events table; MP event ids are
  prefixed "mp_" so they never collide with Stripe event ids.
- tenant.stripe_subscription_id stores the MP preapproval id — the column
  name is legacy, the semantics are "subscription id at the payment provider".
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enums import TenantPlan
from shared.utils.exceptions import ConflictError

from app.config import ApiExecuteSettings
from app.models.stripe_event import StripeEvent
from app.models.tenant import Tenant
from app.services.stripe_service import (
    _apply_plan,
    _normalize_plan,
    _validate_upgrade,
)

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 30.0

PLAN_LABELS = {
    TenantPlan.PLUS: "Crecimiento",
    TenantPlan.PRO: "Corporativo",
}


def _amount_for_plan(plan: TenantPlan, settings: ApiExecuteSettings) -> int:
    mapping = {
        TenantPlan.PLUS: settings.MP_PLAN_AMOUNT_PLUS,
        TenantPlan.PRO: settings.MP_PLAN_AMOUNT_PRO,
    }
    amount = mapping.get(plan, 0)
    if amount <= 0:
        raise ConflictError(
            f"Mercado Pago amount not configured for plan {plan.value}"
        )
    return amount


def _auth_headers(settings: ApiExecuteSettings) -> dict[str, str]:
    if not settings.MP_ACCESS_TOKEN:
        raise ConflictError("Mercado Pago is not configured (MP_ACCESS_TOKEN missing)")
    return {"Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}"}


async def create_subscription_checkout(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_plan: str,
    payer_email: str | None,
    settings: ApiExecuteSettings,
) -> str:
    """Create an MP preapproval (monthly subscription) and return its init_point."""
    from app.services.tenant_service import get_tenant

    tenant = await get_tenant(db, tenant_id)

    requested_plan = _normalize_plan(target_plan)
    if requested_plan is None or requested_plan == TenantPlan.ESTANDAR:
        raise ConflictError("Only paid plans can be purchased")

    current_plan = _normalize_plan(tenant.plan) or TenantPlan.ESTANDAR
    _validate_upgrade(current_plan, requested_plan)

    if not payer_email:
        raise ConflictError("User email is required to start a subscription")

    frontend_url = settings.FRONTEND_URL.rstrip("/")
    label = PLAN_LABELS.get(requested_plan, requested_plan.value)
    body = {
        "reason": f"Sudamérica AI — Plan {label}",
        "external_reference": f"{tenant.id}|{requested_plan.value}",
        "payer_email": payer_email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": _amount_for_plan(requested_plan, settings),
            "currency_id": settings.MP_CURRENCY_ID,
        },
        "back_url": f"{frontend_url}/billing?success=true&plan={requested_plan.value}",
        "status": "pending",
    }

    data = await _create_preapproval(body, settings)
    init_point = data.get("init_point")
    if not init_point:
        logger.error("Mercado Pago preapproval response missing init_point: %s", data)
        raise ConflictError("Mercado Pago returned an invalid response")
    return str(init_point)


async def _create_preapproval(body: dict, settings: ApiExecuteSettings) -> dict:
    """POST /preapproval against the MP API. Isolated for testability."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{settings.MP_API_BASE_URL}/preapproval",
                json=body,
                headers=_auth_headers(settings),
            )
        except httpx.HTTPError as exc:
            logger.error("Mercado Pago preapproval request failed: %s", exc)
            raise ConflictError("Mercado Pago is unreachable, try again later")

    if resp.status_code not in (200, 201):
        logger.error(
            "Mercado Pago preapproval rejected (%s): %s",
            resp.status_code, resp.text[:500],
        )
        raise ConflictError("Mercado Pago rejected the subscription request")
    return resp.json()


# ── Webhook ──────────────────────────────────────────────────────────────────


def _validate_signature(
    x_signature: str,
    x_request_id: str,
    data_id: str,
    secret: str,
) -> bool:
    """Validate MP webhook signature: HMAC-SHA256 over the documented manifest."""
    parts = dict(
        part.strip().split("=", 1)
        for part in x_signature.split(",")
        if "=" in part
    )
    ts, v1 = parts.get("ts"), parts.get("v1")
    if not ts or not v1:
        return False
    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(
        secret.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, v1)


def _parse_external_reference(raw: str | None) -> tuple[uuid.UUID | None, TenantPlan | None]:
    if not raw or "|" not in raw:
        return None, None
    tenant_part, plan_part = raw.split("|", 1)
    try:
        tenant_uuid = uuid.UUID(tenant_part)
    except ValueError:
        return None, _normalize_plan(plan_part)
    return tenant_uuid, _normalize_plan(plan_part)


async def _fetch_preapproval(preapproval_id: str, settings: ApiExecuteSettings) -> dict:
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.MP_API_BASE_URL}/preapproval/{preapproval_id}",
            headers=_auth_headers(settings),
        )
    if resp.status_code != 200:
        raise ConflictError(f"Could not fetch preapproval {preapproval_id} from Mercado Pago")
    return resp.json()


async def _resolve_tenant(
    db: AsyncSession,
    tenant_uuid: uuid.UUID | None,
    preapproval_id: str,
) -> Tenant | None:
    if tenant_uuid:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant
    result = await db.execute(
        select(Tenant).where(Tenant.stripe_subscription_id == preapproval_id)
    )
    return result.scalar_one_or_none()


async def handle_webhook(
    db: AsyncSession,
    *,
    payload: dict,
    data_id_param: str,
    x_signature: str,
    x_request_id: str,
    settings: ApiExecuteSettings,
) -> dict:
    """Process an MP webhook notification (idempotent via stripe_events)."""
    if not settings.MP_WEBHOOK_SECRET:
        logger.warning("MP webhook received but MP_WEBHOOK_SECRET is not configured")
        raise ConflictError("Mercado Pago webhook is not configured")

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    data_id = str(data_id_param or data.get("id") or "")
    if not data_id:
        raise ConflictError("Mercado Pago notification missing data.id")

    if not _validate_signature(x_signature, x_request_id, data_id, settings.MP_WEBHOOK_SECRET):
        logger.warning("MP webhook signature verification failed (data.id=%s)", data_id)
        raise ConflictError("Invalid Mercado Pago webhook signature")

    event_type = str(payload.get("type") or payload.get("topic") or "unknown")
    notification_id = payload.get("id")
    action = str(payload.get("action") or "")
    event_key = (
        f"mp_{notification_id}"
        if notification_id
        else f"mp_{event_type}_{data_id}_{action}"
    )

    # Fast-path for sequential redeliveries (the common MP retry case).
    existing = await db.execute(
        select(StripeEvent).where(StripeEvent.stripe_event_id == event_key)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    # Claim the idempotency key atomically inside a savepoint: if a concurrent
    # delivery already inserted the same event_key, the unique constraint fires
    # and we roll back only the savepoint (the outer tx stays alive) and report
    # already_processed instead of bubbling a 500 to Mercado Pago.
    db_event = StripeEvent(
        stripe_event_id=event_key,
        event_type=f"mp.{event_type}",
        payload=dict(payload),
        processed=False,
    )
    try:
        async with db.begin_nested():
            db.add(db_event)
            await db.flush()
    except IntegrityError:
        return {"status": "already_processed"}

    if event_type == "subscription_preapproval":
        await _handle_preapproval_update(db, data_id, settings)
    else:
        # subscription_authorized_payment and others: stored for audit only.
        logger.info("MP webhook %s stored without action (data.id=%s)", event_type, data_id)

    db_event.processed = True
    await db.flush()
    return {"status": "processed"}


_GRACE_PERIOD = timedelta(days=7)


def _billing_state(tenant: Tenant) -> dict:
    config = tenant.config if isinstance(tenant.config, dict) else {}
    billing = config.get("billing")
    return billing if isinstance(billing, dict) else {}


def _set_billing_state(tenant: Tenant, billing: dict) -> None:
    # Reassign the whole dict so SQLAlchemy detects the JSON column change.
    config = dict(tenant.config) if isinstance(tenant.config, dict) else {}
    config["billing"] = billing
    tenant.config = config


def _start_grace_period(tenant: Tenant) -> None:
    billing = _billing_state(tenant)
    if billing.get("grace_until"):
        return
    grace_until = (datetime.now(timezone.utc) + _GRACE_PERIOD).isoformat()
    _set_billing_state(tenant, {**billing, "grace_until": grace_until})
    logger.warning(
        "Tenant %s payment paused — grace period until %s before downgrade",
        tenant.id, grace_until,
    )


def _grace_period_expired(tenant: Tenant) -> bool:
    raw = _billing_state(tenant).get("grace_until")
    if not raw:
        return False
    try:
        return datetime.now(timezone.utc) >= datetime.fromisoformat(str(raw))
    except (ValueError, TypeError):
        # Unparseable or tz-naive grace_until → treat as expired (fail safe to
        # downgrade rather than leave the tenant on a paid plan indefinitely).
        return True


def _clear_grace_period(tenant: Tenant) -> None:
    billing = _billing_state(tenant)
    if "grace_until" not in billing:
        return
    billing = {key: value for key, value in billing.items() if key != "grace_until"}
    _set_billing_state(tenant, billing)


def _downgrade_to_estandar(tenant: Tenant) -> None:
    estandar = TenantPlan.ESTANDAR
    tenant.plan = estandar.value
    tenant.max_users = estandar.max_users
    tenant.max_leads_mes = estandar.max_leads_mes
    tenant.stripe_subscription_id = None
    _clear_grace_period(tenant)


def apply_pending_downgrade(tenant: Tenant) -> bool:
    """Lazily downgrade a tenant to ESTANDAR if its grace period has expired.

    There is no scheduled job in this project, so the downgrade after a failed
    payment is enforced on-demand: callers that read or gate on plan quotas
    (lead/user limits, /billing/usage) invoke this so an expired grace window
    is resolved the next time the tenant touches a plan-bound action.

    Returns True if the tenant was downgraded.
    """
    if _grace_period_expired(tenant):
        _downgrade_to_estandar(tenant)
        return True
    return False


async def _handle_preapproval_update(
    db: AsyncSession,
    preapproval_id: str,
    settings: ApiExecuteSettings,
) -> None:
    preapproval = await _fetch_preapproval(preapproval_id, settings)
    status = str(preapproval.get("status") or "")
    tenant_uuid, plan = _parse_external_reference(preapproval.get("external_reference"))

    tenant = await _resolve_tenant(db, tenant_uuid, preapproval_id)
    if tenant is None:
        logger.warning(
            "MP preapproval %s (status=%s) has no matching tenant", preapproval_id, status
        )
        return

    if status == "authorized" and plan is not None:
        _apply_plan(tenant, plan, customer_id=None, subscription_id=preapproval_id)
        _clear_grace_period(tenant)
        logger.info("Tenant %s upgraded to %s via MP preapproval %s", tenant.id, plan.value, preapproval_id)
    elif status == "cancelled":
        _downgrade_to_estandar(tenant)
        logger.info("Tenant %s downgraded to ESTANDAR (MP status=cancelled)", tenant.id)
    elif status == "paused":
        # Failed/paused charge: give a grace window before downgrading so a
        # recovered payment keeps the tenant on their plan. The expiry is also
        # enforced lazily on quota reads (apply_pending_downgrade), so the
        # downgrade no longer depends on MP sending a second paused webhook.
        if apply_pending_downgrade(tenant):
            logger.warning(
                "Tenant %s downgraded to ESTANDAR: MP preapproval %s still paused after grace period",
                tenant.id, preapproval_id,
            )
        else:
            _start_grace_period(tenant)
    else:
        logger.info(
            "MP preapproval %s in status=%s — no plan change applied", preapproval_id, status
        )
