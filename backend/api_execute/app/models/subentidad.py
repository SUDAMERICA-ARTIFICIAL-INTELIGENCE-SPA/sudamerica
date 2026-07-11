"""ClienteSubentidad — sub-entidad del cliente (mascota/vehículo/propiedad/paciente), F6."""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class ClienteSubentidad(TenantBase):
    __tablename__ = "cliente_subentidades"
    __table_args__ = {"extend_existing": True}

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    datos: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
