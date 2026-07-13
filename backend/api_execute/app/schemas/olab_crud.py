"""Schemas de dominios chicos de OLA B (B3)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DevolucionResponse(BaseModel):
    id: UUID
    lead_id: UUID | None = None
    venta_id: UUID | None = None
    cliente_nombre: str | None = None
    numero: str
    fecha: date
    motivo: str
    estado: str
    metodo_reembolso: str | None = None
    monto: Decimal
    items: list = []
    notas: str | None = None
    model_config = ConfigDict(from_attributes=True)


class PlantillaResponse(BaseModel):
    id: UUID
    nombre: str
    canal: str
    categoria: str | None = None
    contenido: str
    variables: list = []
    usos: int = 0
    activo: bool = True
    model_config = ConfigDict(from_attributes=True)


class DocumentoResponse(BaseModel):
    id: UUID
    nombre: str
    tipo: str
    categoria: str | None = None
    url: str | None = None
    mime: str | None = None
    tamano_kb: int | None = None
    subido_por: str | None = None
    entidad_tipo: str | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CampanaResponse(BaseModel):
    id: UUID
    nombre: str
    canal: str
    tipo: str
    estado: str
    segmento: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    presupuesto: Decimal
    enviados: int
    abiertos: int
    conversiones: int
    ingresos_generados: Decimal
    model_config = ConfigDict(from_attributes=True)


class CampanaCreate(BaseModel):
    nombre: str
    canal: str = "WHATSAPP"
    tipo: str = "PROMO"
    segmento: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    presupuesto: Decimal = Decimal("0")


class PlantillaCreate(BaseModel):
    nombre: str
    canal: str = "WHATSAPP"
    categoria: str = "GENERAL"
    contenido: str
    variables: list = []
