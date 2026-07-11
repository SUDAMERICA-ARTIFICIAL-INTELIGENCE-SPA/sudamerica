"""Paquete de rubros (SSOT multi-rubro). Re-exporta la API del diccionario."""

from shared.rubros.capacidades import (
    CAPACIDADES,
    CAPACIDADES_META,
    Capacidad,
    CapacidadMeta,
)
from shared.rubros.diccionario import (
    PRIMITIVAS,
    RUBRO_DEFAULT,
    Primitiva,
    Rubro,
    get_rubro,
    resolve_rubro,
    rubro_def,
    rubros_disponibles,
)
from shared.rubros.operativa import (
    estados_orden,
    puede_transicionar,
    roles_equipo,
    tipo_recurso_default,
    transiciones_orden,
)

__all__ = [
    "estados_orden",
    "puede_transicionar",
    "roles_equipo",
    "tipo_recurso_default",
    "transiciones_orden",
    "CAPACIDADES",
    "CAPACIDADES_META",
    "Capacidad",
    "CapacidadMeta",
    "PRIMITIVAS",
    "RUBRO_DEFAULT",
    "Primitiva",
    "Rubro",
    "get_rubro",
    "resolve_rubro",
    "rubro_def",
    "rubros_disponibles",
]
