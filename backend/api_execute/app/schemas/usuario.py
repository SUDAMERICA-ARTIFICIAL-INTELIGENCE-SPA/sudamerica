"""Usuario schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre: str
    apellido: str
    role: str = "PERSONAL"
    sucursal_id: UUID | None = None


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    role: str | None = None
    email_verified: bool | None = None
    sucursal_id: UUID | None = None


class UsuarioResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    nombre: str
    apellido: str
    role: str
    sucursal_id: UUID | None = None
    email_verified: bool
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
