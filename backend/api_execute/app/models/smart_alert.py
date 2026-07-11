"""SmartAlert model for tenant-scoped AI-generated alerts."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class SmartAlert(TenantBase):
    __tablename__ = "smart_alerts"
    __table_args__ = {"extend_existing": True}

    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
