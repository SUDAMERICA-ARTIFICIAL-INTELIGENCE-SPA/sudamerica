"""Lead schemas — LeadUpdate has NO estado field (use LeadTransicion)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from shared.models.enums import LeadEstado


class LeadCreate(BaseModel):
    nombre: str
    email: str | None = None
    telefono: str | None = None
    empresa: str | None = None
    sector: str | None = None
    canal: str | None = None
    valor_estimado: Decimal | None = None
    notas: str | None = None
    asignado_a: UUID | None = None
    intencion: str | None = None
    score: int | None = None


class LeadUpdate(BaseModel):
    """Update lead fields — estado is NOT here, use LeadTransicion."""

    nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    empresa: str | None = None
    sector: str | None = None
    canal: str | None = None
    valor_estimado: Decimal | None = None
    notas: str | None = None
    asignado_a: UUID | None = None
    intencion: str | None = None
    score: int | None = None
    tags: list[str] | None = None


class LeadTransicion(BaseModel):
    """FSM transition request — target estado."""

    estado: str

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        try:
            LeadEstado(v)
        except ValueError:
            valid = [e.value for e in LeadEstado]
            raise ValueError(f"Invalid estado '{v}'. Must be one of: {valid}")
        return v


class LeadResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str
    email: str | None = None
    telefono: str | None = None
    empresa: str | None = None
    sector: str | None = None
    canal: str | None = None
    estado: str
    valor_estimado: Decimal | None = None
    notas: str | None = None
    asignado_a: UUID | None = None
    intencion: str | None = None
    score: int | None = None
    estado_cliente: str | None = None
    total_pedidos: int = 0
    total_gastado: Decimal = Decimal("0")
    plato_favorito: str | None = None
    ultima_visita: date | None = None
    frecuencia_dias: int | None = None
    tags: list[str] | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
