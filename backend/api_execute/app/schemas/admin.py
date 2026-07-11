"""Schemas for /admin/* endpoints (SUPERADMIN only)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


# ── Tenants ──────────────────────────────────────────

class TenantAdminResponse(BaseModel):
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
    user_count: int = 0
    lead_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TenantAdminUpdate(BaseModel):
    nombre: str | None = None
    plan: str | None = None
    max_users: int | None = None
    max_leads_mes: int | None = None
    activo: bool | None = None
    config: dict | None = None


# ── Users ────────────────────────────────────────────

class UserAdminResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    nombre: str
    apellido: str
    role: str
    email_verified: bool
    activo: bool
    created_at: datetime
    updated_at: datetime
    tenant_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserAdminUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    role: str | None = None
    activo: bool | None = None


class ResetPasswordResponse(BaseModel):
    reset_token: str
    temp_password: str
    expires_at: datetime


class SetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class SetPasswordResponse(BaseModel):
    status: str


# ── Metrics ──────────────────────────────────────────

class MetricsOverview(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int
    total_leads_month: int
    total_conversations_today: int
    mrr: float
    active_whatsapp_instances: int


class TimeseriesPoint(BaseModel):
    date: str
    tenants: int
    leads: int
    conversations: int


class TopTenantItem(BaseModel):
    tenant_id: UUID
    tenant_nombre: str
    plan: str
    leads: int
    conversations: int
    users: int


# ── API Keys ─────────────────────────────────────────

class PlatformKeyInfo(BaseModel):
    provider: str
    masked_key: str
    status: str
    balance: float | None = None


class PlatformKeysResponse(BaseModel):
    openai: PlatformKeyInfo | None = None
    gemini: PlatformKeyInfo | None = None


class RotateKeyRequest(BaseModel):
    provider: str
    new_key: str
    reason: str | None = None


class RotateKeyResponse(BaseModel):
    success: bool
    provider: str
    masked_key: str


class TenantKeyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_nombre: str | None = None
    provider: str
    masked_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateTenantKeyRequest(BaseModel):
    tenant_id: UUID
    provider: str
    api_key: str


class KeyUsageItem(BaseModel):
    date: str
    provider: str
    tokens: int
    cost: float


# ── WhatsApp ─────────────────────────────────────────

class WhatsAppInstanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_nombre: str | None = None
    instance_name: str
    status: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReconnectResponse(BaseModel):
    qr_code: str | None = None
    status: str


# ── System ───────────────────────────────────────────

class ServiceHealth(BaseModel):
    name: str
    url: str
    status: str
    latency_ms: float | None = None


class SystemHealthResponse(BaseModel):
    services: list[ServiceHealth]


class ConfigUpdateRequest(BaseModel):
    key: str
    value: dict


class PlatformConfigResponse(BaseModel):
    id: UUID
    key: str
    value: dict
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataModelSummary(BaseModel):
    total_tables: int
    total_columns: int
    tenant_scoped_tables: int
    total_relationships: int


class DataModelEnum(BaseModel):
    name: str
    values: list[str]


class DataModelColumn(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    unique: bool
    default: str | None = None
    foreign_key: str | None = None


class DataModelRelation(BaseModel):
    column: str
    references_table: str
    references_column: str
    on_delete: str | None = None


class DataModelIndex(BaseModel):
    name: str
    columns: list[str]
    unique: bool = False


class DataModelTable(BaseModel):
    name: str
    model_name: str | None = None
    description: str | None = None
    tenant_scoped: bool
    has_soft_delete: bool
    columns: list[DataModelColumn]
    relations: list[DataModelRelation]
    indexes: list[DataModelIndex]


class DataModelResponse(BaseModel):
    generated_at: datetime
    summary: DataModelSummary
    enums: list[DataModelEnum]
    tables: list[DataModelTable]
