"""Tenant schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    nombre: str
    plan: str = "ESTANDAR"
    config: dict | None = None


class TenantUpdate(BaseModel):
    nombre: str | None = None
    plan: str | None = None
    config: dict | None = None


class TenantResponse(BaseModel):
    id: UUID
    nombre: str
    slug: str
    plan: str
    max_users: int
    max_leads_mes: int
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    config: dict | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
