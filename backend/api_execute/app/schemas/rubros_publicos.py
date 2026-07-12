"""Schema del descubrimiento público de rubros (Fase C, Paso 6).

Response del router ``routes/rubros.py`` (``GET /rubros/disponibles``): el set vivo de rubros
seed+runtime activos que la UI de onboarding/registro/admin consume para ofrecer también los
rubros creados en runtime (que NO están en el fixture compilado). No expone metadatos de versión
ni ``updated_by`` (eso es superficie admin); solo el manifiesto necesario para poblar un selector.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RubroDisponible(BaseModel):
    """Un rubro del set vivo (labels/capacidades) para poblar selectores de la UI."""

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
