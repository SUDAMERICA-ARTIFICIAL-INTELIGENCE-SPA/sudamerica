"""Schemas for reservaciones (restaurant table reservations)."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EstadoReservacion = Literal["PENDIENTE", "CONFIRMADA", "CANCELADA", "COMPLETADA", "NO_SHOW"]


class ReservacionCreate(BaseModel):
    mesa_id: UUID | None = None
    lead_id: UUID | None = None
    fecha_reserva: date
    hora_inicio: time
    hora_fin: time | None = None  # auto-calculated if omitted (2h default)
    cantidad_personas: int = Field(..., ge=1, le=50)
    nombre_cliente: str = Field(..., min_length=1, max_length=255)
    rut: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=50)
    notas: str | None = None


class ReservacionUpdate(BaseModel):
    mesa_id: UUID | None = None
    fecha_reserva: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cantidad_personas: int | None = Field(default=None, ge=1, le=50)
    nombre_cliente: str | None = Field(default=None, max_length=255)
    rut: str | None = None
    email: str | None = None
    telefono: str | None = None
    estado: EstadoReservacion | None = None
    notas: str | None = None


class ReservacionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    lead_id: UUID | None = None
    mesa_id: UUID | None = None
    fecha_reserva: date
    hora_inicio: time
    hora_fin: time
    cantidad_personas: int
    nombre_cliente: str
    rut: str | None = None
    email: str | None = None
    telefono: str | None = None
    estado: str
    notas: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DisponibilidadRequest(BaseModel):
    fecha: date
    hora: time
    cantidad_personas: int = Field(..., ge=1, le=50)
    duracion_horas: int = Field(default=2, ge=1, le=6)


class MesaDisponible(BaseModel):
    mesa_id: UUID
    numero: int
    nombre: str | None = None
    capacidad: int


class DisponibilidadResponse(BaseModel):
    disponible: bool
    mesas: list[MesaDisponible] = Field(default_factory=list)
    fecha: date
    hora: time
