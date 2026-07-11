"""Pydantic schemas for revision humana endpoints."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from shared.models.enums import RevisionAccion, RevisionDeliveryStatus

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ConfidenceScore = Annotated[float, Field(ge=0, le=1)]


class RevisionCreate(BaseModel):
    """Schema for creating a new revision entry."""

    lead_id: UUID | None = None
    mensaje_original: NonEmptyText
    respuesta_ia: NonEmptyText
    confianza: ConfidenceScore


class RevisionResponse(BaseModel):
    """Schema for returning a revision entry."""

    id: UUID
    tenant_id: UUID
    lead_id: UUID | None = None
    mensaje_original: str
    respuesta_ia: str
    confianza: float
    accion: RevisionAccion | None = None
    respuesta_editada: str | None = None
    operador_id: UUID | None = None
    procesado: bool
    tiempo_revision_ms: int | None = None
    delivery_status: RevisionDeliveryStatus
    delivery_timestamp: datetime | None = None
    delivery_error: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevisionAccionRequest(BaseModel):
    """Schema for operator action on a revision."""

    accion: Literal[RevisionAccion.EDITAR]
    respuesta_editada: NonEmptyText


class RevisionStats(BaseModel):
    """Aggregated stats for the revision panel."""

    total_pendientes: int
    aprobadas_hoy: int
    editadas_hoy: int
    rechazadas_hoy: int
    tiempo_promedio_ms: float | None = None
    precision_ia: float
