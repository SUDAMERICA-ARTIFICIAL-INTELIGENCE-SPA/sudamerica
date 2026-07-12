"""Schemas for the user-facing agent config endpoints (dashboard).

Mirror of the old AI_dialer ``AgenteConfigResponse`` / ``AgenteConfigUpdate`` so the
dashboard hooks keep their exact request/response shapes. api_execute owns the
``agente_config`` table and serves these over ``GET/PATCH /api/v1/core/ai/config``.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_time_window(value: str | None) -> str | None:
    """Ensure an outbound-window field parses as ``HH:MM`` (or is None)."""
    if value is None:
        return value
    datetime.strptime(value, "%H:%M")
    return value


class AgenteConfigUpdate(BaseModel):
    """PATCH body — every field optional; only present keys are updated."""

    system_prompt: str | None = None
    modelo: str | None = None
    temperatura: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    voz_id: str | None = None
    voz_nombre: str | None = None
    umbral_confianza: float | None = Field(default=None, ge=0.0, le=1.0)
    sub_agentes_activos: dict | None = None
    auto_respuesta_whatsapp: bool | None = None
    outbound_proactivo: bool | None = None
    outbound_horario_inicio: str | None = None  # "HH:MM"
    outbound_horario_fin: str | None = None  # "HH:MM"
    outbound_mensaje_template: str | None = None
    instrucciones_disponibilidad: str | None = None
    knowledge_max_chars: int | None = Field(default=None, ge=500, le=50000)
    session_timeout_minutes: int | None = Field(default=None, ge=1, le=1440)
    nombre_agente: str | None = None
    personalidad: str | None = None
    menu_pdf_url: str | None = None
    debounce_seconds: float | None = Field(default=None, ge=0.0, le=15.0)

    _validate_inicio = field_validator("outbound_horario_inicio", mode="before")(
        _validate_time_window
    )
    _validate_fin = field_validator("outbound_horario_fin", mode="before")(
        _validate_time_window
    )


class AgenteConfigResponse(BaseModel):
    """Full agent config object returned to the dashboard (and read by canales)."""

    id: UUID
    tenant_id: UUID
    system_prompt: str
    modelo: str
    temperatura: float
    max_tokens: int
    voz_id: str | None = None
    voz_nombre: str | None = None
    umbral_confianza: float
    sub_agentes_activos: dict | None = None
    auto_respuesta_whatsapp: bool = True
    outbound_proactivo: bool = False
    outbound_horario_inicio: str | None = None
    outbound_horario_fin: str | None = None
    outbound_mensaje_template: str | None = None
    instrucciones_disponibilidad: str | None = None
    knowledge_max_chars: int = 6000
    session_timeout_minutes: int = 30
    nombre_agente: str | None = None
    personalidad: str | None = None
    menu_pdf_url: str | None = None
    debounce_seconds: float = 4.0
    activo: bool

    model_config = ConfigDict(from_attributes=True)
