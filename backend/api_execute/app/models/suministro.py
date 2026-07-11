"""Suministro (insumo genérico: ingrediente, material, repuesto) + Receta (BOM ítem-insumo)."""

import uuid

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Suministro(TenantBase):
    __tablename__ = "suministros"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_suministro_nombre"),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    unidad: Mapped[str] = mapped_column(String(50), nullable=False, default="unidad")
    stock_actual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock_minimo: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    costo_unitario: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    proveedor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    recetas = relationship("Receta", back_populates="suministro", lazy="selectin")


class Receta(TenantBase):
    __tablename__ = "recetas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "producto_id", "suministro_id", name="uq_receta_prod_sum"),
        {"extend_existing": True},
    )

    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id"), nullable=False
    )
    suministro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suministros.id"), nullable=False
    )
    cantidad_necesaria: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False
    )

    producto = relationship("Producto", lazy="selectin")
    suministro = relationship("Suministro", back_populates="recetas", lazy="selectin")
