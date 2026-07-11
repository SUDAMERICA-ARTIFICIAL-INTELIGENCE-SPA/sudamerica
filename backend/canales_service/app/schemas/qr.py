"""Schemas for WhatsApp QR code onboarding via Evolution API."""

from uuid import UUID

from pydantic import BaseModel, Field


class QRRequest(BaseModel):
    """Request to create a WhatsApp instance and get its QR code."""

    tenant_id: UUID
    instance_name: str


class QRGenerateRequest(BaseModel):
    """Optional body for QR generation — accepts phone number."""

    phone_number: str | None = None


class QRResponse(BaseModel):
    """QR code data returned to the client."""

    qr_code: str
    instance_name: str
    status: str
    integration: str = "WHATSAPP-BAILEYS"


class ProxyConfigRequest(BaseModel):
    """Configure proxy for a Baileys WhatsApp instance."""

    proxy_host: str = Field(..., description="Proxy hostname or IP")
    proxy_port: str = Field(..., description="Proxy port")
    proxy_protocol: str = Field("http", description="http, https, or socks5")
    proxy_username: str | None = Field(None, description="Proxy auth username")
    proxy_password: str | None = Field(None, description="Proxy auth password")


class ProxyConfigResponse(BaseModel):
    """Response after configuring proxy."""

    instance_name: str
    proxy_host: str
    proxy_port: str
    proxy_protocol: str
    status: str


class CloudAPIRegisterRequest(BaseModel):
    """Register a WhatsApp Business Cloud API instance (no QR needed)."""

    meta_token: str = Field(..., description="Permanent token from Meta Business Manager admin")
    meta_number_id: str = Field(..., description="WhatsApp Number ID from Facebook Developers")
    meta_business_id: str = Field(..., description="WhatsApp Business Account ID")
    phone_number: str | None = Field(None, description="Display phone number (e.g. +56912345678)")


class CloudAPIResponse(BaseModel):
    """Response after registering a Cloud API instance."""

    instance_name: str
    status: str
    integration: str = "WHATSAPP-BUSINESS"
    phone_number: str | None = None
