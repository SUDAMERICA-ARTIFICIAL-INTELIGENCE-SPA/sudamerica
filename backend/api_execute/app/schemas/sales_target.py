"""SalesTarget Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class SalesTargetCreate(BaseModel):
    asesor_id: UUID | None = None
    periodo: str  # YYYY-MM
    meta_ventas: float
    meta_leads: int
    meta_conversion: float

    @field_validator("periodo")
    @classmethod
    def validate_periodo(cls, v: str) -> str:
        if len(v) != 7 or v[4] != "-":
            raise ValueError("periodo must be in YYYY-MM format")
        int(v[:4])  # year
        month = int(v[5:])
        if not 1 <= month <= 12:
            raise ValueError("month must be 1-12")
        return v


class SalesTargetResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    asesor_id: UUID | None = None
    periodo: str
    meta_ventas: float
    meta_leads: int
    meta_conversion: float

    model_config = ConfigDict(from_attributes=True)
