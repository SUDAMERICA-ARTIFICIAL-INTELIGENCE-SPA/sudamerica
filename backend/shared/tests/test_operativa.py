"""Tests F4 (operativa multi-rubro): FSM de estados por rubro + roles de equipo.

Puros (sin DB). Crítico: restaurante byte-idéntico (sincronización exacta con
``ComandaEstado.valid_transitions`` y set completo de roles).
"""

import importlib.util
from pathlib import Path

# ``shared.models.__init__`` importa el ORM (sqlalchemy, ausente en el sandbox);
# enums.py solo usa stdlib → se carga por ruta directa para mantener el test puro.
_spec = importlib.util.spec_from_file_location(
    "shared_models_enums",
    Path(__file__).resolve().parents[1] / "models" / "enums.py",
)
assert _spec is not None and _spec.loader is not None
_enums = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_enums)
ComandaEstado = _enums.ComandaEstado
UserRole = _enums.UserRole

from shared.rubros.operativa import (
    estados_orden,
    puede_transicionar,
    roles_equipo,
    transiciones_orden,
)


# ── Sincronización restaurante (byte-idéntico) ───────────────────────────────


def test_fsm_restaurante_sincronizado_con_enum():
    esperado = {
        k.value: tuple(t.value for t in v)
        for k, v in ComandaEstado.valid_transitions().items()
    }
    assert dict(transiciones_orden("restaurante")) == esperado


def test_restaurante_no_puede_usar_en_proceso():
    assert puede_transicionar("restaurante", "PENDIENTE", "EN_PROCESO") is False
    assert "EN_PROCESO" not in estados_orden("restaurante")


def test_roles_restaurante_set_completo():
    roles = set(roles_equipo("restaurante"))
    assert {"MESERO", "COCINA", "CAJA", "GERENTE", "ADMIN"} <= roles


# ── FSM genérico (rubros sin cocina) ─────────────────────────────────────────


def test_ferreteria_fsm_generico():
    assert puede_transicionar("ferreteria", "PENDIENTE", "EN_PROCESO") is True
    assert puede_transicionar("ferreteria", "PENDIENTE", "LISTO") is True  # sin preparación
    assert puede_transicionar("ferreteria", "EN_PROCESO", "LISTO") is True
    assert puede_transicionar("ferreteria", "LISTO", "ENTREGADO") is True
    assert puede_transicionar("ferreteria", "PENDIENTE", "EN_COCINA") is False


def test_estados_terminales_en_ambos_fsm():
    for rubro in ("restaurante", "ferreteria", "peluqueria"):
        assert puede_transicionar(rubro, "ENTREGADO", "PENDIENTE") is False
        assert puede_transicionar(rubro, "CANCELADO", "PENDIENTE") is False


def test_todo_estado_no_terminal_permite_cancelar():
    for rubro in ("restaurante", "ferreteria"):
        for estado, targets in transiciones_orden(rubro).items():
            if targets:
                assert "CANCELADO" in targets, f"{rubro}:{estado}"


def test_estado_desconocido_no_transiciona():
    assert puede_transicionar("ferreteria", "INVENTADO", "LISTO") is False


# ── Roles derivados de módulos ───────────────────────────────────────────────


def test_roles_son_subconjunto_de_userrole():
    validos = {r.value for r in UserRole}
    for rubro in ("restaurante", "peluqueria", "ferreteria"):
        assert set(roles_equipo(rubro)) <= validos


def test_ferreteria_sin_roles_de_sala_ni_cocina():
    roles = roles_equipo("ferreteria")
    assert "MESERO" not in roles
    assert "COCINA" not in roles
    assert "CAJA" in roles


def test_peluqueria_con_rol_de_sala_sin_cocina():
    roles = roles_equipo("peluqueria")
    assert "MESERO" in roles  # módulo RECURSO ON (silla)
    assert "COCINA" not in roles


# ── Tipo de recurso (F5) ─────────────────────────────────────────────────────


def test_tipo_recurso_default_por_rubro():
    from shared.rubros.operativa import tipo_recurso_default

    assert tipo_recurso_default("restaurante") == "mesa"
    assert tipo_recurso_default("peluqueria") == "silla"
    assert tipo_recurso_default("desconocido") == "mesa"  # fail-safe
