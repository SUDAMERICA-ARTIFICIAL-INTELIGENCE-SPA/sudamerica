"""Delivery models — repartidores (drivers) + delivery_assignments."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Repartidor(TenantBase):
    __tablename__ = "repartidores"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_repartidores_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "phone", name="uq_repartidor_tenant_phone"),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)


class DeliveryAssignment(TenantBase):
    __tablename__ = "delivery_assignments"
    __table_args__ = {"extend_existing": True}

    comanda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comandas.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    repartidor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repartidores.id"), nullable=True,
    )
    repartidor_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    repartidor_nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="PUBLICADO")
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)
    monto_a_cobrar: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comanda = relationship("Comanda", lazy="selectin")
    repartidor = relationship("Repartidor", lazy="selectin")
