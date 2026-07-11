"""Producto schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductoCreate(BaseModel):
    categoria_id: UUID | None = None
    nombre: str
    descripcion: str | None = None
    precio: Decimal
    costo: Decimal | None = None
    sku: str | None = None
    imagen_url: str | None = None
    stock: int = 0
    stock_minimo: int = 0
    unidad_venta: str = "unidad"
    disponible: bool = True


class ProductoUpdate(BaseModel):
    categoria_id: UUID | None = None
    nombre: str | None = None
    descripcion: str | None = None
    precio: Decimal | None = None
    costo: Decimal | None = None
    sku: str | None = None
    imagen_url: str | None = None
    stock: int | None = None
    stock_minimo: int | None = None
    unidad_venta: str | None = None
    disponible: bool | None = None


class ProductoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    categoria_id: UUID | None = None
    nombre: str
    descripcion: str | None = None
    precio: Decimal
    costo: Decimal | None = None
    sku: str | None = None
    imagen_url: str | None = None
    stock: int
    stock_minimo: int = 0
    unidad_venta: str = "unidad"
    disponible: bool = True
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductoFilter(BaseModel):
    categoria_id: UUID | None = None
    precio_min: Decimal | None = None
    precio_max: Decimal | None = None
    nombre: str | None = None
    disponible: bool | None = None
