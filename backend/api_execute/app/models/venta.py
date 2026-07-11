"""Venta model — multi-tenant via TenantBase, total is immutable."""

import uuid

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Venta(TenantBase):
    __tablename__ = "ventas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_ventas_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    lead_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    producto_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id"), nullable=True
    )
    usuario_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_entrega: Mapped[str | None] = mapped_column(String(20), nullable=True)
    numero_mesa: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lead = relationship("Lead", lazy="selectin")
    producto = relationship("Producto", lazy="selectin")
    usuario = relationship("Usuario", lazy="selectin")
