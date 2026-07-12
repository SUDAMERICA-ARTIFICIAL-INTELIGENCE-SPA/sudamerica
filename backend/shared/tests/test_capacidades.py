"""Contract tests del catálogo de capacidades (ERP+CRM) y la categorización por rubro.

Puros (sin ORM). Auto-escalan desde el SSOT (100/100 con `capacidades` requerido).
Guardrail crítico: restaurante == {catalogo, agenda, pedidos, pagos, delivery, mesas}
(byte-identidad).
"""

import pytest

from shared.rubros import (
    CAPACIDADES,
    CAPACIDADES_META,
    Capacidad,
    rubro_def,
    rubros_disponibles,
)

RESTAURANTE_CAPACIDADES = (
    Capacidad.CATALOGO,
    Capacidad.AGENDA,
    Capacidad.PEDIDOS,
    Capacidad.PAGOS,
    Capacidad.DELIVERY,
    Capacidad.MESAS,
)

# ── Catálogo ─────────────────────────────────────────────────────────────────


def test_catalogo_es_25_unicas_en_cap_order():
    assert CAPACIDADES == (
        "catalogo",
        "agenda",
        "cotizador",
        "pedidos",
        "pagos",
        "delivery",
        "suscripciones",
        "soporte",
        "proyectos",
        "inventario",
        "compras",
        "produccion",
        "expedientes",
        "contratos",
        "cursos",
        "arriendos",
        "facturacion",
        "fidelizacion",
        "campanas",
        "terreno",
        "mesas",
        "consentimientos",
        "contabilidad",
        "activos_fijos",
        "rrhh",
    )
    assert len(set(CAPACIDADES)) == 25


def test_meta_cubre_todo_el_catalogo():
    assert set(CAPACIDADES_META.keys()) == set(CAPACIDADES)
    for slug, meta in CAPACIDADES_META.items():
        assert meta.slug == slug
        assert meta.label and meta.descripcion and meta.eje


# ── Campo stored por rubro (canónico; endurecido a 100/100 en Etapa B) ───────


def test_restaurante_stored_es_byte_identico():
    """Ancla de compatibilidad: el set stored de restaurante es EXACTAMENTE la
    derivación de sus módulos reales — ni facturación, ni fidelización, ni
    inventario, ni producción."""
    assert rubro_def("restaurante").capacidades == RESTAURANTE_CAPACIDADES


@pytest.mark.parametrize("key", list(rubros_disponibles()))
def test_capacidades_stored_validas_y_en_cap_order(key):
    definicion = rubro_def(key)
    caps = definicion.capacidades
    assert caps, f"{key} sin capacidades (requerido tras 100/100)"
    assert set(caps) <= set(CAPACIDADES), f"slug inventado en {key}"
    assert len(set(caps)) == len(caps), f"duplicados en {key}"
    assert list(caps) == [c for c in CAPACIDADES if c in caps], f"orden no canónico en {key}"
    assert Capacidad.CATALOGO in caps and Capacidad.PAGOS in caps


@pytest.mark.parametrize("key", list(rubros_disponibles()))
def test_sub_entidad_implica_expedientes(key):
    """Invariante relajada F6→capacidades: ficha de sub-entidad ⟹ expedientes."""
    definicion = rubro_def(key)
    if definicion.sub_entidad_label:
        assert Capacidad.EXPEDIENTES in definicion.capacidades


def test_tiene_capacidad_helper():
    assert rubro_def("restaurante").tiene_capacidad(Capacidad.MESAS)
    assert not rubro_def("restaurante").tiene_capacidad(Capacidad.FACTURACION)
