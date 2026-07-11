"""Stripe routes: create-checkout and webhook."""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user

from app.routes.deps import get_settings
from app.schemas.stripe import StripeCheckoutRequest, StripeCheckoutResponse
from app.services import stripe_service

router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/create-checkout", response_model=StripeCheckoutResponse)
async def create_checkout(
    body: StripeCheckoutRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StripeCheckoutResponse:
    """Create a Stripe Checkout session for a paid plan upgrade."""
    settings = get_settings(request)
    url = await stripe_service.create_checkout_session(
        db=db,
        tenant_id=current_user["tenant_id"],
        target_plan=body.plan,
        settings=settings,
    )
    return StripeCheckoutResponse(checkout_url=url, target_plan=body.plan)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(alias="Stripe-Signature"),
):
    """Handle Stripe webhook (idempotent)."""
    settings = get_settings(request)
    payload = await request.body()
    return await stripe_service.handle_webhook(
        db, payload, stripe_signature, settings
    )
