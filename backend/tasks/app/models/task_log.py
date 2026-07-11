"""TaskLog model -- tenant-scoped audit trail for asynchronous task execution."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class TaskTipo(StrEnum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


class TaskEstado(StrEnum):
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    FALLIDO = "FALLIDO"


class TaskLog(Base):
    """Logs every async task (email, whatsapp, sms) with its result."""

    __tablename__ = "task_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    destinatario: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    contenido: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskEstado.PENDIENTE
    )
    error_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
