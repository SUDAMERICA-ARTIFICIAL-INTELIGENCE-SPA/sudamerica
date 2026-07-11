"""Delivery schemas — repartidores and delivery assignments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Repartidor ────────────────────────────────────────────────────────


class RepartidorCreate(BaseModel):
    nombre: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    sucursal_id: UUID | None = None


class RepartidorUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    sucursal_id: UUID | None = None
    activo: bool | None = None


class RepartidorResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sucursal_id: UUID | None = None
    nombre: str
    phone: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── DeliveryAssignment ────────────────────────────────────────────────


class DeliveryClaimRequest(BaseModel):
    """Payload when a driver claims a delivery (from group message)."""
    comanda_id: UUID
    repartidor_phone: str = Field(..., max_length=20)
    repartidor_nombre: str | None = Field(None, max_length=100)


class DeliveryEstadoUpdate(BaseModel):
    estado: str = Field(..., pattern="^(ACEPTADO|EN_RUTA|ENTREGADO|CANCELADO)$")


class DeliveryAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    comanda_id: UUID
    repartidor_id: UUID | None = None
    repartidor_phone: str | None = None
    repartidor_nombre: str | None = None
    estado: str
    metodo_pago: str | None = None
    monto_a_cobrar: float = 0
    claimed_at: datetime | None = None
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
