"""RevisionHumana model for the human review panel."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase
from shared.models.enums import RevisionDeliveryStatus


class RevisionHumana(TenantBase):
    __tablename__ = "revision_humana"

    # FK to leads.id is enforced at the DB level only (leads lives in api_execute).
    # Omitting the SQLAlchemy ForeignKey avoids NoReferencedTableError during
    # mapper resolution in this service, which never loads the Lead model.
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    mensaje_original: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta_ia: Mapped[str] = mapped_column(Text, nullable=False)
    confianza: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    accion: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # APROBAR, EDITAR, RECHAZAR
    respuesta_editada: Mapped[str | None] = mapped_column(Text, nullable=True)
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    procesado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tiempo_revision_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        default=RevisionDeliveryStatus.PENDING.value,
        nullable=False,
        server_default=RevisionDeliveryStatus.PENDING.value,
    )
    delivery_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
