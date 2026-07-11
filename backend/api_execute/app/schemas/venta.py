"""Venta schemas — VentaCreate has NO total field (computed server-side)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VentaCreate(BaseModel):
    """No total field: total = cantidad * precio_unitario (server-side)."""

    lead_id: UUID | None = None
    producto_id: UUID | None = None
    cantidad: int
    precio_unitario: Decimal
    notas: str | None = None
    tipo_entrega: str | None = None
    numero_mesa: int | None = None


class VentaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    lead_id: UUID | None = None
    producto_id: UUID | None = None
    usuario_id: UUID | None = None
    cantidad: int
    precio_unitario: Decimal
    total: Decimal
    notas: str | None = None
    tipo_entrega: str | None = None
    numero_mesa: int | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
