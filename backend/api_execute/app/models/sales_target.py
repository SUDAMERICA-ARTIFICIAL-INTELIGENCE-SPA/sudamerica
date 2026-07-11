"""SalesTarget model for monthly team/advisor goals."""

import uuid

from sqlalchemy import Integer, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class SalesTarget(TenantBase):
    __tablename__ = "sales_targets"
    __table_args__ = {"extend_existing": True}

    asesor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    meta_ventas: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    meta_leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta_conversion: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
