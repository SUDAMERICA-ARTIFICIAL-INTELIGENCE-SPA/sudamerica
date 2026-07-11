"""Sucursal model — per-tenant location (branch/store), multi-tenant."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class Sucursal(TenantBase):
    """A physical location (branch) belonging to a tenant."""

    __tablename__ = "sucursales"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_sucursales_tenant_id_id"),
        UniqueConstraint("tenant_id", "slug", name="uq_sucursal_tenant_slug"),
        UniqueConstraint("tenant_id", "nombre", name="uq_sucursal_tenant_nombre"),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    horario: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    zona_delivery: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    es_principal: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pais: Mapped[str] = mapped_column(String(3), default="CL", nullable=False)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    costo_delivery: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    grupo_repartidores_jid: Mapped[str | None] = mapped_column(String(60), nullable=True)
