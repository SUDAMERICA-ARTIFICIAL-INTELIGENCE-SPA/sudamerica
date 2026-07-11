"""Mesa schemas — restaurant table CRUD."""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MesaCreate(BaseModel):
    numero: int = Field(..., ge=1)
    nombre: str | None = None
    capacidad: int = Field(default=4, ge=1, le=100)
    sucursal_id: UUID | None = None
    # F5: tipo de recurso (mesa/silla/box…); si falta, el servicio lo deriva del rubro.
    tipo: str | None = Field(default=None, max_length=30)


class MesaUpdate(BaseModel):
    nombre: str | None = None
    capacidad: int | None = Field(default=None, ge=1, le=100)
    sucursal_id: UUID | None = None


class MesaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sucursal_id: UUID | None = None
    numero: int
    nombre: str | None = None
    capacidad: int
    tipo: str = "mesa"
    qr_token: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MesaDisponibilidadItem(BaseModel):
    id: UUID
    numero: int
    capacidad: int
    zona: str | None = None


class MesaDisponibilidadLegacyItem(MesaDisponibilidadItem):
    mesa_id: UUID


class MesaDisponibilidadResponse(BaseModel):
    disponibles: list[MesaDisponibilidadItem]
    mesas: list[MesaDisponibilidadLegacyItem]
    fecha: date
    hora: time
    personas: int
