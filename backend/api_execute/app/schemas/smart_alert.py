"""SmartAlert Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SmartAlertResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    lead_id: UUID | None = None
    mensaje: str
    leido: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SmartAlertUpdate(BaseModel):
    leido: bool | None = None
