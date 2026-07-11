"""Modifier schemas — groups + individual modifiers."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from shared.models.enums import ModifierGroupTipo


# --- Modifier (option within a group) ---

class ModifierCreate(BaseModel):
    nombre: str
    precio_delta: Decimal = Decimal("0")
    orden: int = 0


class ModifierUpdate(BaseModel):
    nombre: str | None = None
    precio_delta: Decimal | None = None
    orden: int | None = None
    activo: bool | None = None


class ModifierResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    grupo_id: UUID
    nombre: str
    precio_delta: Decimal
    orden: int
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Modifier Group ---

class ModifierGroupCreate(BaseModel):
    nombre: str
    tipo: str
    obligatorio: bool = False
    max_selecciones: int | None = None
    modifiers: list[ModifierCreate] | None = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        try:
            ModifierGroupTipo(v)
        except ValueError:
            valid = [e.value for e in ModifierGroupTipo]
            raise ValueError(f"Invalid tipo '{v}'. Must be one of: {valid}")
        return v


class ModifierGroupUpdate(BaseModel):
    nombre: str | None = None
    tipo: str | None = None
    obligatorio: bool | None = None
    max_selecciones: int | None = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ModifierGroupTipo(v)
        except ValueError:
            valid = [e.value for e in ModifierGroupTipo]
            raise ValueError(f"Invalid tipo '{v}'. Must be one of: {valid}")
        return v


class ModifierGroupResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str
    tipo: str
    obligatorio: bool
    max_selecciones: int | None = None
    modifiers: list[ModifierResponse] = []
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Product ↔ Modifier Group assignment ---

class ProductoModifierGroupAssign(BaseModel):
    modifier_group_ids: list[UUID]
