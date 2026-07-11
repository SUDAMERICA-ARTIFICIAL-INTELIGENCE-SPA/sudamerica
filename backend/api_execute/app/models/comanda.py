"""Comanda models — comandas + comanda_items (kitchen order system)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TenantBase


class Comanda(TenantBase):
    __tablename__ = "comandas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_comandas_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    venta_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ventas.id"), nullable=True
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    tipo_entrega: Mapped[str] = mapped_column(String(20), nullable=False)  # MESA | DELIVERY | RETIRO
    numero_mesa: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE")
    canal_origen: Mapped[str] = mapped_column(String(20), nullable=False)  # WHATSAPP | WEB | PRESENCIAL
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    prioridad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tiempo_estimado_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entregado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Delivery fields
    direccion_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)
    ubicacion_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    ubicacion_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)
    costo_delivery: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    pago_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    repartidor_nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    repartidor_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    items = relationship("ComandaItem", back_populates="comanda", lazy="selectin", cascade="all, delete-orphan")
    cliente = relationship("Lead", lazy="selectin")
    venta = relationship("Venta", lazy="selectin")


class ComandaItem(Base):
    __tablename__ = "comanda_items"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comanda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comandas.id", ondelete="CASCADE"), nullable=False
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    costo_unitario: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    modifiers_json: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    comanda = relationship("Comanda", back_populates="items")
    producto = relationship("Producto", lazy="selectin")
