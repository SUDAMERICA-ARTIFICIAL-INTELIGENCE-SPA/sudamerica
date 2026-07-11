"""Lead model — multi-tenant via TenantBase, with FSM estado."""

import uuid

from sqlalchemy import Date, ForeignKey, ForeignKeyConstraint, Integer, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Lead(TenantBase):
    __tablename__ = "leads"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_leads_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    canal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="NUEVO", nullable=False)
    valor_estimado: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    asignado_a: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    intencion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Fidelización fields (Fase 2)
    estado_cliente: Mapped[str | None] = mapped_column(
        String(20), default="NUEVO", nullable=True
    )
    total_pedidos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_gastado: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, server_default="0"
    )
    plato_favorito: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ultima_visita: Mapped[str | None] = mapped_column(Date, nullable=True)
    frecuencia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    asignado = relationship("Usuario", lazy="selectin")
