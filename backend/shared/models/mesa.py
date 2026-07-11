"""Mesa model — recurso físico reservable (mesa/silla/box…), multi-tenant, per-sucursal.

F5 multi-rubro (fase expand): la tabla conserva el nombre ``mesas`` por compat;
``tipo`` tipifica el recurso. El contract (rename a ``recursos``) queda diferido.

Lives in shared/ so services that reference it via FK (e.g. ai-dialer's
Session.mesa_id) can register the Mesa table in Base.metadata at startup
without crossing service boundaries.
"""

import uuid

from sqlalchemy import ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class Mesa(TenantBase):
    __tablename__ = "mesas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "sucursal_id"],
            ["sucursales.tenant_id", "sucursales.id"],
            name="fk_mesas_sucursal_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "sucursal_id", "numero", name="uq_mesas_tenant_sucursal_numero"),
        {"extend_existing": True},
    )

    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacidad: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default="mesa", nullable=False)
    qr_token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
