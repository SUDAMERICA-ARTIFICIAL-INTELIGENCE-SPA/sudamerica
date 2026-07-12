"""Registro con caché en proceso del manifiesto de rubro (Fase B, Paso 5).

La verdad de AUTORÍA y el FALLBACK siguen siendo ``shared/rubros/diccionario.py`` (funciones
puras, síncronas, sin cambio de firma). Este registro **lee en runtime** los rubros desde la tabla
BD global ``rubros`` (seedeada como proyección de ``diccionario.py`` vía el fixture) a un dict de
``Rubro`` cacheado en proceso, y expone accesores **síncronos equivalentes** a los de
``diccionario`` (``rubro_def`` / ``resolve_rubro`` / ``rubros_disponibles``) leyendo del caché.

Propiedades clave:

- **No vuelve async** las funciones puras: el caché se carga en el ``lifespan`` (o tras cada
  escritura del CRUD admin vía :func:`refresh`); los accesores son síncronos.
- **Fallback fail-safe loggeado** a ``diccionario._RUBROS`` si la tabla está vacía/indisponible o
  la carga falla → el sistema nunca cae frente al cliente y, en tests sin BD, el registro delega
  transparentemente en la fuente de código.
- **Una sola verdad:** con la tabla seedeada, ``rubro_def(k)`` produce un ``Rubro`` *idéntico* al
  de ``diccionario.rubro_def(k)`` para toda clave (invariante testeada).
- **Anclaje de versión (Fase B, §5):** un ContextVar por-tarea fija la versión del manifiesto que
  debe servirse durante la composición de un mensaje; el registro guarda un caché **acotado** de
  las últimas versiones y sirve el snapshot anclado (con fallback-a-vigente **loggeado** si la
  versión anclada expiró del caché).
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Iterator, Mapping

from shared.rubros import diccionario as _dic
from shared.rubros.diccionario import RUBRO_DEFAULT, Rubro

if TYPE_CHECKING:  # sqlalchemy solo se importa (perezoso) en refresh(); mantiene el módulo puro.
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Número de versiones históricas del manifiesto que se mantienen en memoria para el anclaje.
# Una conversación cuya versión anclada haya caído fuera de esta ventana se resuelve a la versión
# vigente (loggeado): el anclaje es best-effort acotado, no snapshots persistidos (§10.2 default).
_MAX_SNAPSHOTS = 16

# Estado del registro (módulo-global, un solo proceso).
_current: dict[str, Rubro] = {}
_version: int = 0
_snapshots: "OrderedDict[int, dict[str, Rubro]]" = OrderedDict()

# Versión anclada para la tarea/mensaje en curso (None ⟺ usar la vigente).
_anchor: ContextVar[int | None] = ContextVar("rubro_manifest_anchor", default=None)


# ── Construcción del Rubro desde una fila BD ─────────────────────────────────


def _as_container(value: Any, default: Any) -> Any:
    """JSONB puede llegar ya deserializado (dict/list) o como str según el driver."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def _row_to_rubro(row: Mapping[str, Any]) -> Rubro:
    """Reconstruye el ``Rubro`` (mismo dataclass frozen) desde una fila de la tabla ``rubros``."""
    labels = _as_container(row["labels"], {})
    capacidades = _as_container(row["capacidades"], [])
    semillas = _as_container(row["categorias_semilla"], [])
    return Rubro(
        key=row["key"],
        nombre=row["nombre"],
        emoji=row["emoji"],
        sector=row["sector"],
        labels=MappingProxyType(dict(labels)),
        categorias_semilla=tuple(semillas),
        sub_entidad_label=row["sub_entidad_label"],
        capacidades=tuple(capacidades),
        recurso=bool(row["recurso"]),
        variantes=bool(row["variantes"]),
        precio_medida=bool(row["precio_medida"]),
    )


# ── Carga / refresh desde la BD ──────────────────────────────────────────────


async def refresh(db: AsyncSession) -> int:
    """(Re)carga el caché desde la tabla ``rubros`` + el contador global de versión.

    Devuelve la versión vigente cargada. Fail-safe **loggeado** a ``diccionario._RUBROS`` (versión
    ``0``) si la tabla está vacía/indisponible o la carga falla — el registro nunca deja el
    proceso sin manifiesto servible.
    """
    from sqlalchemy import text  # import perezoso: mantiene el módulo puro (fase-A).

    global _current, _version
    try:
        # Fase C (Paso 6): carga la UNIÓN de seed+runtime pero SOLO las filas activas. Un rubro
        # runtime desactivado (activo=false) desaparece del roster vigente; las conversaciones
        # ancladas a una versión previa siguen viéndolo vía su snapshot en `_snapshots`.
        result = await db.execute(
            text(
                "SELECT key, nombre, emoji, sector, labels, capacidades, "
                "sub_entidad_label, recurso, variantes, precio_medida, categorias_semilla "
                "FROM rubros WHERE activo = TRUE"
            )
        )
        rows = result.mappings().all()
        if not rows:
            logger.warning(
                "rubro_registry: tabla 'rubros' vacía; fallback a diccionario.py (fail-safe)."
            )
            _current = {}
            _version = 0
            return 0

        cache = {row["key"]: _row_to_rubro(row) for row in rows}
        version = await _load_version(db)

        _current = cache
        _version = version
        _snapshots[version] = cache
        while len(_snapshots) > _MAX_SNAPSHOTS:
            _snapshots.popitem(last=False)  # evicta la versión más antigua
        logger.info("rubro_registry: cargados %d rubros (versión %d)", len(cache), version)
        return version
    except Exception:
        logger.warning(
            "rubro_registry: fallo al cargar desde BD; fallback a diccionario.py (fail-safe).",
            exc_info=True,
        )
        _current = {}
        _version = 0
        return 0


# Alias semántico para el arranque.
load = refresh


async def _load_version(db: AsyncSession) -> int:
    """Lee el contador global ``rubro_manifest_version`` de ``platform_config`` (default 1)."""
    from sqlalchemy import text  # import perezoso (fase-A: módulo puro).

    try:
        result = await db.execute(
            text("SELECT value FROM platform_config WHERE key = 'rubro_manifest_version'")
        )
        value = result.scalar_one_or_none()
        if value is None:
            return 1
        data = value if isinstance(value, dict) else json.loads(value)
        return int(data.get("version", 1))
    except Exception:
        logger.warning("rubro_registry: no se pudo leer rubro_manifest_version; asumiendo 1.")
        return 1


# ── Anclaje de versión (ContextVar por tarea) ────────────────────────────────


def current_version() -> int:
    """Versión vigente del manifiesto (0 si el registro no está cargado → fallback a código)."""
    return _version


@contextmanager
def anchored(version: int | None) -> Iterator[None]:
    """Ancla la versión del manifiesto para el bloque (composición de un mensaje).

    ``version=None`` es no-op (se usa la vigente). Preserva el valor a través de ``await`` dentro
    de la misma tarea (semántica de ContextVar); se restaura al salir del bloque.
    """
    token = _anchor.set(version)
    try:
        yield
    finally:
        _anchor.reset(token)


def _active_cache() -> dict[str, Rubro]:
    """Caché a servir según la versión anclada (o la vigente); {} si el registro no está cargado."""
    if not _current:
        return {}
    version = _anchor.get()
    if version is None or version == _version:
        return _current
    snapshot = _snapshots.get(version)
    if snapshot is None:
        logger.info(
            "rubro_registry: versión anclada %d fuera del caché acotado; sirviendo la vigente %d.",
            version,
            _version,
        )
        return _current
    return snapshot


# ── Accesores síncronos (equivalentes a diccionario, DB-backed con fallback) ──


def rubro_def(key: str | None) -> Rubro:
    """Definición del rubro desde el caché (anclado); fail-safe a ``restaurante``.

    Sirve indistintamente rubros ``seed`` y ``runtime`` activos (Fase C): ambos viven en el mismo
    caché ``_current`` reconstruido desde la tabla. Si el registro no está cargado (tabla
    vacía/indisponible, o entorno de test sin BD) delega en la función pura
    ``diccionario.rubro_def`` → comportamiento idéntico a antes de la Fase B. Nota (§4.4): con BD
    caída, una ``key`` de un rubro **runtime** (que no existe en ``diccionario.py``) cae al
    fail-safe ``RUBRO_DEFAULT``; el aviso loggeado de ese fail-safe lo emite el consumidor de
    tenant (``tenant_rubro.load_tenant_rubro``), no este accesor puro/caliente.
    """
    cache = _active_cache()
    if not cache:
        return _dic.rubro_def(key)
    if key is None:
        return cache.get(RUBRO_DEFAULT) or _dic.rubro_def(key)
    return cache.get(key) or cache.get(RUBRO_DEFAULT) or _dic.rubro_def(key)


def resolve_rubro(config: Mapping[str, Any] | None) -> str:
    """Resuelve la clave de rubro desde un ``config`` de tenant (fail-safe ``restaurante``).

    Usa el roster vigente del caché (la clave del tenant no se ancla por versión). Fallback puro si
    el registro no está cargado. El roster seedeado == el de ``diccionario`` → idéntico hoy.
    """
    if not _current:
        return _dic.resolve_rubro(config)
    if not config:
        return RUBRO_DEFAULT
    key = config.get("rubro")
    if not isinstance(key, str) or key not in _current:
        return RUBRO_DEFAULT
    return key


def rubros_disponibles() -> tuple[str, ...]:
    """Claves de rubro del set vivo: unión de seed+runtime **activos** (Fase C).

    El caché ``_current`` ya contiene solo filas ``activo=true`` (ver :func:`refresh`), así que la
    unión sale directa de sus claves. Fallback puro al roster **solo-seed** de ``diccionario.py``
    si el registro no está cargado (los rubros runtime no tienen fuente de código).
    """
    if not _current:
        return _dic.rubros_disponibles()
    return tuple(_current.keys())
