"""Fase A (Paso 4) — gating de tools del copiloto por capacidad del tenant.

Restaurante (mesas+pedidos+agenda) conserva las 28 tools (byte-idéntico); un rubro sin
esas capacidades no ve las tools gastronómicas (crear_mesa, comandas, reservaciones).
"""

from app.services.tools import TOOL_CAPABILITY, TOOL_DEFINITIONS, tools_for_capabilities


def _names(tools):
    return {t["function"]["name"] for t in tools}


def test_capabilities_none_expone_todas():
    # Compat: un caller que no envía capacidades ve todas las tools.
    assert tools_for_capabilities(None) == TOOL_DEFINITIONS


def test_restaurante_conserva_todas_las_tools():
    from shared.rubros import rubro_def

    caps = list(rubro_def("restaurante").capacidades)
    assert _names(tools_for_capabilities(caps)) == _names(TOOL_DEFINITIONS)


def test_inmobiliaria_no_ve_tools_gastronomicas():
    from shared.rubros import rubro_def

    caps = list(rubro_def("inmobiliaria").capacidades)  # agenda sí; mesas/pedidos no
    names = _names(tools_for_capabilities(caps))
    # Gastronómicas fuera:
    for gated in ("crear_mesa", "consultar_mesas", "modificar_mesa", "eliminar_mesa",
                  "consultar_comandas", "cambiar_estado_comanda",
                  "consultar_disponibilidad_mesas"):
        assert gated not in names, gated
    # Agenda presente → reservaciones sí; core siempre:
    assert "crear_reservacion" in names
    assert {"consultar_ventas", "consultar_clientes", "consultar_metricas"} <= names


def test_mapping_solo_referencia_tools_reales():
    # El mapping no debe referenciar tools inexistentes (drift guard).
    real = _names(TOOL_DEFINITIONS)
    assert set(TOOL_CAPABILITY) <= real


def test_pedidos_sin_mesas_ve_comandas_no_mesas():
    # Un rubro con pedidos pero sin mesas (p.ej. ferretería) ve comandas, no mesas.
    from shared.rubros import rubro_def

    caps = list(rubro_def("ferreteria").capacidades)
    names = _names(tools_for_capabilities(caps))
    assert "consultar_comandas" in names
    assert "crear_mesa" not in names
