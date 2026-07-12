"""Fase B (Paso 5) — invariante seed↔código del registro de rubro (sin BD).

Reconstruye cada ``Rubro`` desde el fixture commiteado (``frontend/lib/__fixtures__/
rubros.manifest.json``, la verdad-py de la que deriva el seed SQL) usando la MISMA lógica
fila→``Rubro`` del registro (``rubro_registry._row_to_rubro``) y lo compara con
``diccionario.rubro_def(key)``. Esto cierra el eslabón **fixture↔código** de la cadena de una
sola verdad ``diccionario.py ⇒ fixture ⇒ seed``:

- ``frontend/lib/rubros.seed.test.ts`` guarda **seed↔fixture** (el SQL commiteado == regen).
- ``frontend/lib/rubros.parity.test.ts`` guarda **fixture↔espejo ts**.
- este test guarda **fixture↔código** (y, con `_row_to_rubro`, que la reconstrucción del
  registro desde una fila es fiel al dataclass de autoría).

Juntos, cualquier divergencia entre las tres proyecciones falla en CI. No necesita BD: la fila
que ``_row_to_rubro`` espera tiene exactamente las claves de una entrada del fixture, así que la
entrada del fixture se le pasa directamente — el mismo camino que el registro recorre desde la
tabla ``rubros`` seedeada.
"""

import json
from pathlib import Path

import pytest

from app.services.rubro_registry import _row_to_rubro
from shared.rubros import diccionario, rubros_disponibles

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "frontend" / "lib" / "__fixtures__" / "rubros.manifest.json"
)


def _fixture_rubros() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["rubros"]


def test_fixture_cubre_todo_el_roster():
    """El fixture (fuente del seed) cubre exactamente el roster de código."""
    fixture = _fixture_rubros()
    assert set(fixture) == set(rubros_disponibles())
    assert len(fixture) >= 101


@pytest.mark.parametrize("key", sorted(_fixture_rubros().keys()))
def test_rubro_reconstruido_igual_al_codigo(key):
    """Reconstruir el ``Rubro`` desde la fila (como el registro desde la tabla) == código.

    Garantiza el invariante seed↔código: con la tabla seedeada del fixture, el registro produce
    un ``Rubro`` idéntico al de ``diccionario.py`` para cada clave. Cualquier deriva (fixture
    editado sin actualizar el código, o viceversa) hace fallar este test.
    """
    reconstruido = _row_to_rubro(_fixture_rubros()[key])
    assert reconstruido == diccionario.rubro_def(key)


def test_restaurante_byte_identico():
    """Oráculo de no-regresión (Paso 4): restaurante reconstruido == restaurante de código."""
    reconstruido = _row_to_rubro(_fixture_rubros()["restaurante"])
    assert reconstruido == diccionario.rubro_def("restaurante")
