"""Evolution API instance model — maps WhatsApp instances to tenants."""

import uuid

from sqlalchemy import ForeignKeyConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class EvolutionInstance(TenantBase):
    """A WhatsApp instance registered in Evolution API, owned by a tenant."""

    __tablename__ = "evolution_instances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_evolution_instances_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    instance_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DISCONNECTED",
    )
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evo_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integration: Mapped[str] = mapped_column(
        String(30), nullable=False, default="WHATSAPP-BAILEYS",
    )
    meta_business_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta_number_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
