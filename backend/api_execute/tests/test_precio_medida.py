"""Tests F7 M4 (precio por medida): sufijo de unidad y subtotal cotizado. Puros."""

import pytest

from app.services.precio_medida import sufijo_unidad, subtotal_medida


# ── sufijo_unidad (formato del catálogo IA) ──────────────────────────────────


def test_sufijo_vacio_para_venta_por_unidad():
    # Restaurante byte-idéntico: default y 'unidad' no agregan sufijo.
    assert sufijo_unidad(None) == ""
    assert sufijo_unidad("unidad") == ""
    assert sufijo_unidad("") == ""
    assert sufijo_unidad("  ") == ""


def test_sufijo_para_unidades_de_medida():
    assert sufijo_unidad("kg") == "/kg"
    assert sufijo_unidad("m2") == "/m2"
    assert sufijo_unidad("hora") == "/hora"
    assert sufijo_unidad(" kg ") == "/kg"


# ── subtotal_medida (cotización) ─────────────────────────────────────────────


def test_subtotal_por_unidad_entera():
    assert subtotal_medida(1000, 3) == 3000.0
    assert subtotal_medida(1000, 3, "unidad") == 3000.0


def test_subtotal_fraccional_con_unidad_de_medida():
    assert subtotal_medida(9990, 1.5, "kg") == 14985.0
    assert subtotal_medida(2500, 0.25, "kg") == 625.0


def test_subtotal_redondea_a_moneda():
    assert subtotal_medida(0.1, 3, "kg") == 0.3


def test_fraccional_sin_unidad_de_medida_falla():
    with pytest.raises(ValueError):
        subtotal_medida(1000, 1.5)
    with pytest.raises(ValueError):
        subtotal_medida(1000, 1.5, "unidad")


def test_cantidades_y_precios_invalidos():
    with pytest.raises(ValueError):
        subtotal_medida(1000, 0, "kg")
    with pytest.raises(ValueError):
        subtotal_medida(1000, -1)
    with pytest.raises(ValueError):
        subtotal_medida(-5, 1)
