"""Schemas del dominio Compras/Proveedores (OLA B)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProveedorResponse(BaseModel):
    id: UUID
    nombre: str
    rut: str | None = None
    contacto_nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    categoria: str | None = None
    condicion_pago: str | None = None
    lead_time_dias: int | None = None
    rating: Decimal | None = None
    activo: bool = True
    # agregados (CxP y actividad)
    cxp: Decimal = Decimal("0")
    total_comprado: Decimal = Decimal("0")
    ordenes_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class OCItemResponse(BaseModel):
    id: UUID
    producto_id: UUID | None = None
    descripcion: str
    cantidad: Decimal
    cantidad_recibida: Decimal
    costo_unitario: Decimal
    subtotal: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrdenCompraResponse(BaseModel):
    id: UUID
    proveedor_id: UUID
    proveedor_nombre: str | None = None
    numero: str
    estado: str
    fecha_emision: date
    fecha_esperada: date | None = None
    moneda: str = "CLP"
    neto: Decimal
    iva: Decimal
    total: Decimal
    items_count: int = 0
    items: list[OCItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RecepcionResponse(BaseModel):
    id: UUID
    orden_compra_id: UUID
    oc_numero: str | None = None
    proveedor_nombre: str | None = None
    numero: str
    fecha: date
    estado: str
    recibido_por: str | None = None
    items_count: int = 0
    total_unidades: Decimal = Decimal("0")
    model_config = ConfigDict(from_attributes=True)


class FacturaProveedorResponse(BaseModel):
    id: UUID
    proveedor_id: UUID
    proveedor_nombre: str | None = None
    orden_compra_id: UUID | None = None
    numero: str
    fecha_emision: date
    fecha_vencimiento: date | None = None
    estado: str
    neto: Decimal
    iva: Decimal
    total: Decimal
    monto_pagado: Decimal
    saldo: Decimal = Decimal("0")
    metodo_pago: str | None = None
    model_config = ConfigDict(from_attributes=True)


class RequisicionResponse(BaseModel):
    id: UUID
    numero: str
    solicitante: str | None = None
    estado: str
    prioridad: str
    fecha: date
    items: list = []
    notas: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CotizacionResponse(BaseModel):
    id: UUID
    proveedor_id: UUID
    proveedor_nombre: str | None = None
    numero: str
    estado: str
    fecha: date
    validez_dias: int
    total: Decimal
    items: list = []
    model_config = ConfigDict(from_attributes=True)


class EvaluacionProveedor(BaseModel):
    proveedor_id: UUID
    nombre: str
    categoria: str | None = None
    rating: Decimal | None = None
    ordenes_totales: int = 0
    ordenes_recibidas: int = 0
    puntualidad_pct: float = 0
    cumplimiento_pct: float = 0
    total_comprado: Decimal = Decimal("0")
    lead_time_dias: int | None = None


class ComprasResumen(BaseModel):
    proveedores_activos: int = 0
    total_comprado_12m: Decimal = Decimal("0")
    cxp_total: Decimal = Decimal("0")
    cxp_vencida: Decimal = Decimal("0")
    ordenes_abiertas: int = 0
    ordenes_mes: int = 0
    facturas_pendientes: int = 0


# ── Create/Update (CRUD básico de proveedores) ──

class ProveedorCreate(BaseModel):
    nombre: str
    rut: str | None = None
    contacto_nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    categoria: str | None = None
    condicion_pago: str = "CONTADO"
    lead_time_dias: int = 7


class ProveedorUpdate(BaseModel):
    nombre: str | None = None
    rut: str | None = None
    contacto_nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    categoria: str | None = None
    condicion_pago: str | None = None
    lead_time_dias: int | None = None
    rating: Decimal | None = None
    activo: bool | None = None
