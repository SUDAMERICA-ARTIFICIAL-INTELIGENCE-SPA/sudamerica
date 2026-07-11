"""Schemas de sub-entidades del cliente (F6 multi-rubro)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubentidadCreate(BaseModel):
    lead_id: UUID
    tipo: str = Field(..., max_length=30)  # mascota / vehiculo / propiedad / paciente
    nombre: str = Field(..., max_length=255)
    datos: dict = Field(default_factory=dict)


class SubentidadUpdate(BaseModel):
    tipo: str | None = Field(default=None, max_length=30)
    nombre: str | None = Field(default=None, max_length=255)
    datos: dict | None = None


class SubentidadResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    lead_id: UUID
    tipo: str
    nombre: str
    datos: dict
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
