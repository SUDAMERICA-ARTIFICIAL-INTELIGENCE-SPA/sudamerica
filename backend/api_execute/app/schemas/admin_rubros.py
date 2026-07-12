"""Schemas del CRUD admin de rubro (Fase B, Paso 5).

Request/response del router ``routes/admin_rubros.py`` (edición en runtime del manifiesto de
rubro persistido en la tabla global ``rubros``). La validación de negocio (labels completos +
capacidades conocidas, fail-closed 422) la hace ``RubroManifest`` en la capa de servicio; aquí
solo se define la forma de entrada/salida HTTP. ``key`` es inmutable → no es editable.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RubroUpdateRequest(BaseModel):
    """Patch parcial de un rubro. Solo los campos presentes se aplican (``exclude_unset``).

    ``labels`` se fusiona con las existentes en la capa de servicio (editar una primitiva sin
    reenviar las 12). Un manifiesto resultante inválido se rechaza con 422.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    emoji: str | None = None
    sector: str | None = None
    labels: dict[str, str] | None = None
    capacidades: list[str] | None = None
    sub_entidad_label: str | None = None
    recurso: bool | None = None
    variantes: bool | None = None
    precio_medida: bool | None = None
    categorias_semilla: list[str] | None = None


class RubroResponse(BaseModel):
    """Rubro persistido tal como vive en la tabla ``rubros`` (manifiesto + metadatos de versión)."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    nombre: str
    emoji: str
    sector: str
    labels: dict[str, str]
    capacidades: list[str]
    sub_entidad_label: str | None = None
    recurso: bool
    variantes: bool
    precio_medida: bool
    categorias_semilla: list[str]
    version: int
    updated_at: datetime | None = None
    updated_by: UUID | None = None
