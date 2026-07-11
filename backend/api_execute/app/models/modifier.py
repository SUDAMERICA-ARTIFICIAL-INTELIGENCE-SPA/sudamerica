"""Modifier models — modifier_groups, modifiers, producto_modifier_groups."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase, Base


class ModifierGroup(TenantBase):
    __tablename__ = "modifier_groups"
    __table_args__ = {"extend_existing": True}

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # SINGLE_SELECT | MULTI_SELECT
    obligatorio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_selecciones: Mapped[int | None] = mapped_column(Integer, nullable=True)

    modifiers = relationship("Modifier", back_populates="grupo", lazy="selectin")


class Modifier(TenantBase):
    __tablename__ = "modifiers"
    __table_args__ = {"extend_existing": True}

    grupo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modifier_groups.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    precio_delta: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    grupo = relationship("ModifierGroup", back_populates="modifiers", lazy="selectin")


class ProductoModifierGroup(Base):
    """M:N association between productos and modifier_groups."""
    __tablename__ = "producto_modifier_groups"
    __table_args__ = {"extend_existing": True}

    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True
    )
    modifier_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modifier_groups.id", ondelete="CASCADE"), primary_key=True
    )
