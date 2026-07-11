"""Billing routes (provider-agnostic): create-checkout + Mercado Pago webhook.

POST /billing/create-checkout dispatches to the provider configured in
PAYMENT_PROVIDER ("mercadopago" default, "stripe" legacy). The Stripe-specific
routes under /stripe remain for backwards compatibility.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.models.enums import TenantPlan
from shared.utils.exceptions import NotFoundError

from app.models.lead import Lead
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.routes.deps import get_settings
from app.schemas.billing import (
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingUsageResponse,
)
from app.services import mercadopago_service, stripe_service
from app.services.stripe_service import _normalize_plan

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/usage", response_model=BillingUsageResponse)
async def billing_usage(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingUsageResponse:
    """Current consumption vs plan quotas (same queries the limits enforce)."""
    tenant_id = current_user["tenant_id"]
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise NotFoundError("Tenant", str(tenant_id))

    # Lazy enforcement: if a failed-payment grace window has expired, downgrade
    # now (there is no scheduler) so the quotas and flags below reflect reality.
    mercadopago_service.apply_pending_downgrade(tenant)

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )
    leads_used = (await db.scalar(
        select(func.count()).where(Lead.tenant_id == tenant_id, Lead.created_at >= month_start)
    )) or 0
    users_used = (await db.scalar(
        select(func.count()).where(Usuario.tenant_id == tenant_id, Usuario.activo.is_(True))
    )) or 0

    config = tenant.config if isinstance(tenant.config, dict) else {}
    billing_cfg = config.get("billing") if isinstance(config.get("billing"), dict) else {}
    grace_until = billing_cfg.get("grace_until")

    # Normalize away the deprecated FREE label (maps to ESTANDAR).
    plan = (_normalize_plan(tenant.plan) or TenantPlan.ESTANDAR).value
    # A subscription is "active" only when present AND not in a failing grace
    # window; grace_until being non-null signals the payment is failing.
    subscription_active = bool(tenant.stripe_subscription_id) and grace_until is None

    return BillingUsageResponse(
        plan=plan,
        leads_used=leads_used,
        leads_limit=tenant.max_leads_mes,
        users_used=users_used,
        users_limit=tenant.max_users,
        subscription_active=subscription_active,
        grace_until=str(grace_until) if grace_until else None,
    )


@router.post("/create-checkout", response_model=BillingCheckoutResponse)
async def create_checkout(
    body: BillingCheckoutRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingCheckoutResponse:
    """Create a subscription checkout for a paid plan upgrade."""
    settings = get_settings(request)
    if settings.PAYMENT_PROVIDER == "stripe":
        url = await stripe_service.create_checkout_session(
            db=db,
            tenant_id=current_user["tenant_id"],
            target_plan=body.plan,
            settings=settings,
        )
    else:
        url = await mercadopago_service.create_subscription_checkout(
            db=db,
            tenant_id=current_user["tenant_id"],
            target_plan=body.plan,
            payer_email=current_user.get("email"),
            settings=settings,
        )
    return BillingCheckoutResponse(
        checkout_url=url,
        target_plan=body.plan,
        provider=settings.PAYMENT_PROVIDER,
    )


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    data_id: str = Query(default="", alias="data.id"),
    x_signature: str = Header(default="", alias="x-signature"),
    x_request_id: str = Header(default="", alias="x-request-id"),
):
    """Handle Mercado Pago webhook notifications (idempotent)."""
    settings = get_settings(request)
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return await mercadopago_service.handle_webhook(
        db,
        payload=payload,
        data_id_param=data_id,
        x_signature=x_signature,
        x_request_id=x_request_id,
        settings=settings,
    )
