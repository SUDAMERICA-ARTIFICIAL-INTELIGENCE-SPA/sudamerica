"""Categoria model — multi-tenant via TenantBase."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class Categoria(TenantBase):
    __tablename__ = "categorias"
    __table_args__ = {"extend_existing": True}

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
