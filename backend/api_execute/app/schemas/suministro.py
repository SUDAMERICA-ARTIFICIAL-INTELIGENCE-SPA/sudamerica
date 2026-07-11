"""Schemas for suministros (insumos genéricos) and recetas (BOM ítem-insumo)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Suministro ──

class SuministroCreate(BaseModel):
    nombre: str
    unidad: str = "unidad"
    stock_actual: Decimal = Decimal("0")
    stock_minimo: Decimal = Decimal("0")
    costo_unitario: Decimal | None = None
    proveedor: str | None = None


class SuministroUpdate(BaseModel):
    nombre: str | None = None
    unidad: str | None = None
    stock_actual: Decimal | None = None
    stock_minimo: Decimal | None = None
    costo_unitario: Decimal | None = None
    proveedor: str | None = None


class SuministroResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    costo_unitario: Decimal | None = None
    proveedor: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Receta ──

class RecetaCreate(BaseModel):
    producto_id: UUID
    suministro_id: UUID
    cantidad_necesaria: Decimal


class RecetaUpdate(BaseModel):
    cantidad_necesaria: Decimal | None = None


class RecetaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    producto_id: UUID
    suministro_id: UUID
    cantidad_necesaria: Decimal
    activo: bool
    created_at: datetime
    updated_at: datetime

    # Nested names for display
    producto_nombre: str | None = None
    suministro_nombre: str | None = None
    suministro_unidad: str | None = None

    model_config = ConfigDict(from_attributes=True)
