"""Export canónico del manifiesto de rubros (Fase A, Paso 4).

Fuente única = ``diccionario.py`` (py). Este módulo emite un **JSON determinista** con los
campos CONTRACTUALES de cada rubro para que el frontend (espejo ``lib/rubros.ts``) lo
verifique por un test de paridad (``frontend/lib/rubros.parity.test.ts``). Módulo PURO:
solo importa ``shared.rubros`` (sin ORM/DB), ejecutable con un Python de stdlib.

Regenerar el fixture (cuando cambie ``diccionario.py``/``capacidades.py``):

    python backend/shared/rubros/export_manifest.py > frontend/lib/__fixtures__/rubros.manifest.json

El JSON es la verdad-py commiteada; si el espejo ts diverge en cualquier campo contractual,
el test de paridad falla. La FSM/operativa NO se re-serializa (es derivada pura de
``capacidades``+``recurso``; la valida ``operativa.test.ts``).
"""

from __future__ import annotations

import json

from shared.rubros import CAPACIDADES, PRIMITIVAS, RUBRO_DEFAULT, rubro_def, rubros_disponibles


def _rubro_entry(key: str) -> dict:
    """Proyección contractual de un rubro (orden determinista de labels por PRIMITIVAS)."""
    r = rubro_def(key)
    return {
        "key": r.key,
        "nombre": r.nombre,
        "emoji": r.emoji,
        "sector": r.sector,
        "labels": {p: r.labels[p] for p in PRIMITIVAS},
        "capacidades": list(r.capacidades),
        "sub_entidad_label": r.sub_entidad_label,
        "recurso": r.recurso,
        "variantes": r.variantes,
        "precio_medida": r.precio_medida,
        "categorias_semilla": list(r.categorias_semilla),
    }


def build_manifest() -> dict:
    """Manifiesto canónico completo (rubros ordenados alfabéticamente por clave)."""
    return {
        "rubro_default": RUBRO_DEFAULT,
        "primitivas": list(PRIMITIVAS),
        "capacidades": list(CAPACIDADES),
        "rubros": {key: _rubro_entry(key) for key in sorted(rubros_disponibles())},
    }


def dumps() -> str:
    """Serialización determinista (indent=2, unicode preservado, sin sort_keys global:
    el orden ya es explícito por construcción)."""
    return json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    import sys

    sys.stdout.write(dumps())
