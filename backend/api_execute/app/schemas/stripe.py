"""Schemas for Stripe billing endpoints."""

from pydantic import BaseModel, Field


class StripeCheckoutRequest(BaseModel):
    plan: str = Field(default="PRO", pattern="^(PLUS|PRO)$")


class StripeCheckoutResponse(BaseModel):
    checkout_url: str
    target_plan: str
