"""Pydantic schemas for sucursales (multi-location)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SucursalCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    direccion: str | None = None
    telefono: str | None = Field(None, max_length=50)
    horario: dict | None = None
    zona_delivery: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    config: dict | None = None
    ciudad: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    codigo_postal: str | None = Field(None, max_length=20)
    pais: str = Field(default="CL", max_length=3)
    google_maps_url: str | None = None
    costo_delivery: float = 0
    grupo_repartidores_jid: str | None = Field(None, max_length=60)


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    direccion: str | None = None
    telefono: str | None = Field(None, max_length=50)
    horario: dict | None = None
    zona_delivery: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    config: dict | None = None
    ciudad: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    codigo_postal: str | None = Field(None, max_length=20)
    pais: str | None = Field(None, max_length=3)
    google_maps_url: str | None = None
    costo_delivery: float | None = None
    grupo_repartidores_jid: str | None = Field(None, max_length=60)


class SucursalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str
    slug: str
    direccion: str | None
    telefono: str | None
    horario: dict | None
    zona_delivery: str | None
    latitud: float | None
    longitud: float | None
    config: dict | None
    es_principal: bool
    ciudad: str | None = None
    region: str | None = None
    codigo_postal: str | None = None
    pais: str = "CL"
    google_maps_url: str | None = None
    costo_delivery: float = 0
    grupo_repartidores_jid: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
