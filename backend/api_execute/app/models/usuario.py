"""Usuario model — multi-tenant via TenantBase."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import TenantBase


class Usuario(TenantBase):
    __tablename__ = "usuarios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_usuarios_sucursal_tenant",
            ondelete="SET NULL",
        ),
        {"extend_existing": True},
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="ASESOR", nullable=False)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email_verification_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant = relationship("Tenant", lazy="selectin")
