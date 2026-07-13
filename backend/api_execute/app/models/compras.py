"""Modelos del dominio Compras/Proveedores (OLA B).

Grafo de coherencia: OrdenCompra → Recepcion (entrada stock) → FacturaProveedor (egreso/CxP).
"""

import uuid

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TenantBase


class Proveedor(TenantBase):
    __tablename__ = "proveedores"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="proveedores_tenant_id_nombre_key"),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    rut: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contacto_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True)
    condicion_pago: Mapped[str | None] = mapped_column(String(40), default="CONTADO")
    lead_time_dias: Mapped[int | None] = mapped_column(Integer, default=7)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrdenCompra(TenantBase):
    __tablename__ = "ordenes_compra"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="ordenes_compra_tenant_id_numero_key"),
        {"extend_existing": True},
    )

    proveedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("proveedores.id"), nullable=False)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    fecha_emision: Mapped[Date] = mapped_column(Date, nullable=False)
    fecha_esperada: Mapped[Date | None] = mapped_column(Date, nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), default="CLP")
    neto: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    iva: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    items = relationship("OCItem", lazy="selectin", cascade="all, delete-orphan")


class OCItem(Base):
    __tablename__ = "oc_items"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orden_compra_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_compra.id"), nullable=False)
    producto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    cantidad_recibida: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    costo_unitario: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), default=0)


class Recepcion(TenantBase):
    __tablename__ = "recepciones"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="recepciones_tenant_id_numero_key"),
        {"extend_existing": True},
    )

    orden_compra_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_compra.id"), nullable=False)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="COMPLETA")
    recibido_por: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    items = relationship("RecepcionItem", lazy="selectin", cascade="all, delete-orphan")


class RecepcionItem(Base):
    __tablename__ = "recepcion_items"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recepcion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recepciones.id"), nullable=False)
    oc_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("oc_items.id"), nullable=True)
    producto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("productos.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    costo_unitario: Mapped[float] = mapped_column(Numeric(14, 2), default=0)


class FacturaProveedor(TenantBase):
    __tablename__ = "facturas_proveedor"
    __table_args__ = (
        UniqueConstraint("tenant_id", "proveedor_id", "numero", name="facturas_proveedor_tenant_id_proveedor_id_numero_key"),
        {"extend_existing": True},
    )

    proveedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("proveedores.id"), nullable=False)
    orden_compra_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_compra.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_emision: Mapped[Date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[Date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    neto: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    iva: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    monto_pagado: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Requisicion(TenantBase):
    __tablename__ = "requisiciones"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="requisiciones_tenant_id_numero_key"),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    solicitante: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    prioridad: Mapped[str] = mapped_column(String(10), default="MEDIA")
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    items: Mapped[list] = mapped_column(JSON, default=list)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class Cotizacion(TenantBase):
    __tablename__ = "cotizaciones"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="cotizaciones_tenant_id_numero_key"),
        {"extend_existing": True},
    )

    proveedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("proveedores.id"), nullable=False)
    requisicion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("requisiciones.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="RECIBIDA")
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    validez_dias: Mapped[int] = mapped_column(Integer, default=15)
    total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    items: Mapped[list] = mapped_column(JSON, default=list)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
