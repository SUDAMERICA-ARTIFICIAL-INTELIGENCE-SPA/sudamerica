"""Fase C (Paso 6) — validación fail-closed de crear rubro runtime + ciclo de vida.

Cubre las reglas que NO requieren una BD real (se ejecutan antes de tocarla, o con ``get_rubro`` /
``_tenants_using_rubro`` monkeypatcheados): key bien formada/no reservada, manifiesto válido, y las
protecciones del ciclo de vida (un seed no se desactiva; ``RUBRO_DEFAULT`` protegido; guardrail de
uso rechaza si hay tenants). Los caminos que escriben en la tabla (persistencia + bump + refresh) se
verifican por lectura (sin python/docker en el host).
"""

import pytest

from app.services import admin_service
from app.services.admin_service import (
    _RUBRO_KEY_RE,
    _code_roster,
    create_rubro,
    set_rubro_activo,
)
from shared.rubros import PRIMITIVAS, RUBRO_DEFAULT
from shared.utils.exceptions import ConflictError, UnprocessableError


def _manifiesto_valido(key: str = "arriendo_carros") -> dict:
    """Manifiesto de rubro completo y válido (12 labels + capacidad conocida)."""
    return {
        "key": key,
        "nombre": "Arriendo de Carros",
        "emoji": "🚙",
        "sector": "otro",
        "labels": {p: p.capitalize() for p in PRIMITIVAS},
        "capacidades": ["catalogo"],
        "sub_entidad_label": None,
        "recurso": False,
        "variantes": True,
        "precio_medida": False,
        "categorias_semilla": ["Sedán", "SUV"],
    }


# ── key format / reserved namespace ──────────────────────────────────


@pytest.mark.parametrize("key", ["arriendo_carros", "x_y_z", "a12", "rubro_runtime_1"])
def test_key_regex_acepta_slugs_validos(key):
    assert _RUBRO_KEY_RE.match(key)


@pytest.mark.parametrize("key", ["Mayus", "con espacio", "ab", "1empieza_num", "tílde", ""])
def test_key_regex_rechaza_malformadas(key):
    assert not _RUBRO_KEY_RE.match(key)


def test_code_roster_incluye_restaurante():
    roster = _code_roster()
    assert "restaurante" in roster
    assert len(roster) >= 101


async def test_create_rechaza_key_malformada_422():
    m = _manifiesto_valido("Bad Key")
    with pytest.raises(UnprocessableError):
        await create_rubro(None, m)  # db no se toca: falla antes


async def test_create_rechaza_key_reservada_por_codigo_409():
    m = _manifiesto_valido("restaurante")  # colisiona con un rubro seed
    with pytest.raises(ConflictError):
        await create_rubro(None, m)


async def test_create_rechaza_manifiesto_invalido_422():
    m = _manifiesto_valido("rubro_nuevo_ok")
    del m["labels"]["catalogo"]  # labels incompletos ⇒ RubroManifest 422
    with pytest.raises(UnprocessableError):
        await create_rubro(None, m)


async def test_create_rechaza_capacidad_desconocida_422():
    m = _manifiesto_valido("rubro_nuevo_ok")
    m["capacidades"] = ["capacidad_inexistente"]
    with pytest.raises(UnprocessableError):
        await create_rubro(None, m)


# ── ciclo de vida ────────────────────────────────────────────────────


def _stub_get_rubro(monkeypatch, row: dict):
    async def _fake(_db, _key):
        return row
    monkeypatch.setattr(admin_service, "get_rubro", _fake)


async def test_desactivar_seed_rechazado_409(monkeypatch):
    _stub_get_rubro(monkeypatch, {"origen": "seed", "activo": True, "key": "restaurante"})
    with pytest.raises(ConflictError):
        await set_rubro_activo(None, "restaurante", False)


async def test_desactivar_default_rechazado_409(monkeypatch):
    # Aunque estuviese marcado runtime (no puede), RUBRO_DEFAULT nunca se desactiva.
    _stub_get_rubro(
        monkeypatch, {"origen": "runtime", "activo": True, "key": RUBRO_DEFAULT}
    )
    with pytest.raises(ConflictError):
        await set_rubro_activo(None, RUBRO_DEFAULT, False)


async def test_desactivar_runtime_con_tenants_rechazado_409(monkeypatch):
    _stub_get_rubro(monkeypatch, {"origen": "runtime", "activo": True, "key": "rt_x"})

    async def _tenants(_db, _key):
        return ["tenant-1", "tenant-2"]

    monkeypatch.setattr(admin_service, "_tenants_using_rubro", _tenants)
    with pytest.raises(ConflictError):
        await set_rubro_activo(None, "rt_x", False)


async def test_activar_seed_rechazado_409(monkeypatch):
    _stub_get_rubro(monkeypatch, {"origen": "seed", "activo": True, "key": "cafeteria"})
    with pytest.raises(ConflictError):
        await set_rubro_activo(None, "cafeteria", True)


async def test_noop_idempotente_sin_cambio_devuelve_fila(monkeypatch):
    # Reactivar un runtime ya activo: no-op idempotente (no bump, no db). Devuelve la fila.
    row = {"origen": "runtime", "activo": True, "key": "rt_x"}
    _stub_get_rubro(monkeypatch, row)
    result = await set_rubro_activo(None, "rt_x", True)
    assert result == row
