"""Contract tests for the rubro dictionary (SSOT) — Fase 0 multi-rubro.

These tests are pure (no ORM / DB): they import only ``shared.rubros`` and verify
the vocabulary/module contract and, critically, that the default rubro reproduces
the current restaurant behaviour (backwards-compatibility guardrail).
"""

from types import SimpleNamespace

import pytest

from shared.rubros import (
    PRIMITIVAS,
    RUBRO_DEFAULT,
    Capacidad,
    Rubro,
    get_rubro,
    resolve_rubro,
    rubro_def,
    rubros_disponibles,
)

# ── Default / backwards-compatibility ────────────────────────────────────────


def test_default_rubro_is_restaurante():
    assert RUBRO_DEFAULT == "restaurante"


@pytest.mark.parametrize("config", [None, {}, {"otra_clave": 1}, {"rubro": None}])
def test_resolve_rubro_defaults_to_restaurante(config):
    """Un tenant sin `rubro` (o con valor vacío) se comporta como restaurante."""
    assert resolve_rubro(config) == RUBRO_DEFAULT


def test_resolve_rubro_reads_config_key():
    assert resolve_rubro({"rubro": "peluqueria"}) == "peluqueria"
    assert resolve_rubro({"rubro": "ferreteria"}) == "ferreteria"


def test_unknown_rubro_is_failsafe_to_default():
    """Un rubro desconocido NO rompe: cae a restaurante (fail-safe en prod)."""
    assert resolve_rubro({"rubro": "rubro_inexistente"}) == RUBRO_DEFAULT
    assert rubro_def("rubro_inexistente").key == RUBRO_DEFAULT


def test_get_rubro_duck_types_tenant_config():
    tenant = SimpleNamespace(config={"rubro": "peluqueria"})
    assert get_rubro(tenant) == "peluqueria"
    tenant_sin_config = SimpleNamespace(config=None)
    assert get_rubro(tenant_sin_config) == RUBRO_DEFAULT
    assert get_rubro(SimpleNamespace()) == RUBRO_DEFAULT  # sin atributo config


# ── Registry / contract completeness ─────────────────────────────────────────


def test_expected_rubros_present():
    keys = set(rubros_disponibles())
    assert {"restaurante", "peluqueria", "ferreteria"} <= keys


@pytest.mark.parametrize(
    "key",
    list(rubros_disponibles()),
)
def test_every_rubro_labels_all_primitivas(key):
    """Contrato: todo rubro define una etiqueta para las claves canónicas."""
    definicion = rubro_def(key)
    assert set(definicion.labels.keys()) == set(PRIMITIVAS)
    assert all(isinstance(v, str) and v for v in definicion.labels.values())


@pytest.mark.parametrize(
    "key",
    list(rubros_disponibles()),
)
def test_capacidades_y_seeds_present(key):
    definicion = rubro_def(key)
    assert len(definicion.categorias_semilla) >= 1
    # catálogo y pagos son universales
    assert Capacidad.CATALOGO in definicion.capacidades
    assert Capacidad.PAGOS in definicion.capacidades


# ── Per-rubro semantics (7 ejes de variación) ────────────────────────────────


def test_restaurante_keeps_full_operativa():
    r = rubro_def("restaurante")
    for capacidad in (Capacidad.MESAS, Capacidad.AGENDA, Capacidad.DELIVERY, Capacidad.PEDIDOS):
        assert r.tiene_capacidad(capacidad), f"restaurante debe conservar {capacidad}"
    assert r.recurso  # sala con recurso físico reservable (Mesa)
    assert r.labels["recurso"] == "Mesa"
    assert r.labels["orden"] == "Comanda"
    # `inventario` (stock por ítem) OFF: los insumos van por Suministro/Receta,
    # flujo incondicional no gateado por capacidad → restaurante byte-idéntico (F3).
    assert not r.tiene_capacidad(Capacidad.INVENTARIO)


def test_peluqueria_servicio_con_cita_sin_cocina():
    r = rubro_def("peluqueria")
    assert r.tiene_capacidad(Capacidad.AGENDA)
    assert r.recurso
    assert not r.tiene_capacidad(Capacidad.MESAS)
    assert not r.tiene_capacidad(Capacidad.DELIVERY)
    assert not r.tiene_capacidad(Capacidad.INVENTARIO)
    assert r.labels["item"] == "Servicio"


def test_ferreteria_retail_con_stock_sin_agenda():
    r = rubro_def("ferreteria")
    assert r.tiene_capacidad(Capacidad.INVENTARIO)
    assert not r.tiene_capacidad(Capacidad.AGENDA)
    assert not r.tiene_capacidad(Capacidad.MESAS)


# ── Immutability ─────────────────────────────────────────────────────────────


def test_rubro_definition_is_frozen():
    r = rubro_def("restaurante")
    with pytest.raises((AttributeError, TypeError)):
        r.nombre = "otro"  # frozen dataclass
    with pytest.raises(TypeError):
        r.labels["item"] = "hack"  # labels es un mapping inmutable
