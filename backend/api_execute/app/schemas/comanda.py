"""Comanda schemas — kitchen order system."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from shared.models.enums import CanalOrigen, ComandaEstado, TipoEntrega


# --- Comanda Item ---

class ComandaItemCreate(BaseModel):
    producto_id: UUID
    cantidad: int = 1
    modifiers_json: list[dict] = []
    notas: str | None = None


class ComandaItemResponse(BaseModel):
    id: UUID
    comanda_id: UUID
    producto_id: UUID
    cantidad: int
    precio_unitario: Decimal
    modifiers_json: list[dict]
    subtotal: Decimal
    notas: str | None = None
    producto_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Comanda ---

class ComandaCreate(BaseModel):
    cliente_id: UUID | None = None
    tipo_entrega: str
    numero_mesa: int | None = None
    canal_origen: str
    notas: str | None = None
    prioridad: int = 0
    tiempo_estimado_min: int | None = None
    items: list[ComandaItemCreate]

    @field_validator("tipo_entrega")
    @classmethod
    def validate_tipo_entrega(cls, v: str) -> str:
        try:
            TipoEntrega(v)
        except ValueError:
            valid = [e.value for e in TipoEntrega]
            raise ValueError(f"Invalid tipo_entrega '{v}'. Must be one of: {valid}")
        return v

    @field_validator("canal_origen")
    @classmethod
    def validate_canal_origen(cls, v: str) -> str:
        try:
            CanalOrigen(v)
        except ValueError:
            valid = [e.value for e in CanalOrigen]
            raise ValueError(f"Invalid canal_origen '{v}'. Must be one of: {valid}")
        return v


class ComandaTransicion(BaseModel):
    estado: str

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        try:
            ComandaEstado(v)
        except ValueError:
            valid = [e.value for e in ComandaEstado]
            raise ValueError(f"Invalid estado '{v}'. Must be one of: {valid}")
        return v


class ComandaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sucursal_id: UUID | None = None
    venta_id: UUID | None = None
    cliente_id: UUID | None = None
    tipo_entrega: str
    numero_mesa: int | None = None
    estado: str
    canal_origen: str
    notas: str | None = None
    prioridad: int
    tiempo_estimado_min: int | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime
    entregado_at: datetime | None = None
    # Delivery fields
    direccion_entrega: str | None = None
    ubicacion_lat: float | None = None
    ubicacion_lng: float | None = None
    metodo_pago: str | None = None
    costo_delivery: float = 0
    pago_confirmado: bool = False
    repartidor_nombre: str | None = None
    repartidor_phone: str | None = None
    items: list[ComandaItemResponse] = []
    cliente_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)
