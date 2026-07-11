"""Producto model — multi-tenant via TenantBase."""

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Producto(TenantBase):
    __tablename__ = "productos"
    __table_args__ = {"extend_existing": True}

    categoria_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categorias.id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    precio: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    costo: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=None
    )
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unidad_venta: Mapped[str] = mapped_column(String(20), default="unidad", nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categoria = relationship("Categoria", lazy="selectin")
