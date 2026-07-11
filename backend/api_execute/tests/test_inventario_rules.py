"""Tests F3 (inventario multi-rubro): reglas puras de stock bajo + gating por rubro.

Puros (sin DB): umbral de la alerta ``stock_bajo``, mensajes, línea de stock del
glosario y el gating INVENTARIO (OFF en restaurante → byte-idéntico).
"""

from app.services.inventario_rules import (
    ALERTA_STOCK_BAJO,
    cruza_stock_minimo,
    mensaje_stock_bajo,
)
from app.services.rubro_prompt import build_glosario, incluye_capacidad
from shared.rubros import Capacidad


# ── Umbral (cruce de stock_minimo) ───────────────────────────────────────────


def test_cruce_del_umbral_alerta():
    # Arrange: mínimo 5 / Act+Assert: 6 → 4 cruza el umbral
    assert cruza_stock_minimo(6, 4, 5) is True


def test_llegar_exacto_al_minimo_alerta():
    assert cruza_stock_minimo(6, 5, 5) is True


def test_ya_bajo_el_umbral_no_realerta():
    assert cruza_stock_minimo(4, 2, 5) is False


def test_sobre_el_minimo_no_alerta():
    assert cruza_stock_minimo(10, 6, 5) is False


def test_minimo_cero_solo_alerta_al_agotarse():
    assert cruza_stock_minimo(3, 1, 0) is False
    assert cruza_stock_minimo(1, 0, 0) is True


def test_tipo_de_alerta_estable():
    # Contrato con el filtro `tipo` de GET /alertas y el front
    assert ALERTA_STOCK_BAJO == "stock_bajo"


# ── Mensajes ─────────────────────────────────────────────────────────────────


def test_mensaje_stock_bajo_incluye_datos():
    m = mensaje_stock_bajo("Tornillo 3mm", 2, 5, item_label="Artículo")
    assert "Tornillo 3mm" in m
    assert "2" in m and "5" in m


def test_mensaje_agotado_usa_label_del_rubro():
    m = mensaje_stock_bajo("Clavos", 0, 0, item_label="Artículo")
    assert "sin stock" in m.lower()
    assert m.startswith("Artículo")


# ── Gating por rubro (IA + backend respetan Capacidad.INVENTARIO) ────────────


def test_inventario_on_ferreteria_off_restaurante_y_peluqueria():
    assert incluye_capacidad("ferreteria", Capacidad.INVENTARIO) is True
    # Restaurante lleva insumos vía Suministro/Receta (flujo incondicional),
    # NO stock por ítem → sin alertas/vistas nuevas → byte-idéntico.
    assert incluye_capacidad("restaurante", Capacidad.INVENTARIO) is False
    assert incluye_capacidad("peluqueria", Capacidad.INVENTARIO) is False


def test_glosario_ferreteria_menciona_stock():
    g = build_glosario("ferreteria")
    assert "stock" in g
    assert "[NO DISPONIBLE]" in g


def test_glosario_peluqueria_sin_linea_de_stock():
    assert "stock" not in build_glosario("peluqueria")
