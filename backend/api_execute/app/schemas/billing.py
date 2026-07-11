"""Schemas for provider-agnostic SaaS billing endpoints."""

from pydantic import BaseModel, Field


class BillingCheckoutRequest(BaseModel):
    plan: str = Field(default="PRO", pattern="^(PLUS|PRO)$")


class BillingCheckoutResponse(BaseModel):
    checkout_url: str
    target_plan: str
    provider: str


class BillingUsageResponse(BaseModel):
    plan: str
    leads_used: int
    leads_limit: int
    users_used: int
    users_limit: int
    subscription_active: bool
    grace_until: str | None = None
