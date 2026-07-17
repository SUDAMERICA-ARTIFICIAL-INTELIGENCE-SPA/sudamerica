"""Modelos de dominios chicos de OLA B (B3): devoluciones, plantillas, documentos, campañas."""

import uuid

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class Devolucion(TenantBase):
    __tablename__ = "devoluciones"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="devoluciones_tenant_id_numero_key"),
        {"extend_existing": True},
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    venta_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ventas.id"), nullable=True)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(String(60), default="OTRO")
    estado: Mapped[str] = mapped_column(String(20), default="SOLICITADA")
    metodo_reembolso: Mapped[str | None] = mapped_column(String(30), nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    items: Mapped[list] = mapped_column(JSON, default=list)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class MensajePlantilla(TenantBase):
    __tablename__ = "mensaje_plantillas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="mensaje_plantillas_tenant_id_nombre_key"),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    canal: Mapped[str] = mapped_column(String(20), default="WHATSAPP")
    categoria: Mapped[str | None] = mapped_column(String(40), default="GENERAL")
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSON, default=list)
    usos: Mapped[int] = mapped_column(Integer, default=0)


class DocumentoArchivo(TenantBase):
    __tablename__ = "documentos_archivos"
    __table_args__ = ({"extend_existing": True},)

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default="OTRO")
    categoria: Mapped[str | None] = mapped_column(String(60), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tamano_kb: Mapped[int | None] = mapped_column(Integer, default=0)
    subido_por: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entidad_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Campana(TenantBase):
    __tablename__ = "campanas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="campanas_tenant_id_nombre_key"),
        {"extend_existing": True},
    )

    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    canal: Mapped[str] = mapped_column(String(20), default="WHATSAPP")
    tipo: Mapped[str] = mapped_column(String(30), default="PROMO")
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    segmento: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_inicio: Mapped[Date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[Date | None] = mapped_column(Date, nullable=True)
    presupuesto: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    enviados: Mapped[int] = mapped_column(Integer, default=0)
    abiertos: Mapped[int] = mapped_column(Integer, default=0)
    conversiones: Mapped[int] = mapped_column(Integer, default=0)
    ingresos_generados: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
