"""Categoria schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None


class CategoriaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class CategoriaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str
    descripcion: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
