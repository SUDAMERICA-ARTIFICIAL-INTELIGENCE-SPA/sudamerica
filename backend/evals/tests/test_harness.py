"""E2 — Tests del harness (sin red): extracción ast, messages, asserts, cap."""

import pytest

from evals.fixtures import load_fixture
from evals.harness import (
    CostCap,
    _parse_monto,
    build_full_system_prompt,
    build_messages,
    check_asserts,
    extract_behavioral_rules,
)


def test_behavioral_rules_extraidas_del_fuente():
    rules = extract_behavioral_rules()
    assert rules.startswith("REGLAS DE COMPORTAMIENTO")
    assert "No inventes información" in rules


def test_full_prompt_replica_chat_service():
    fx = load_fixture("restaurante")
    full = build_full_system_prompt(fx)
    # chat_service.py: system_prompt_override + "\n\n" + BEHAVIORAL_RULES
    assert full.endswith("\n\n" + extract_behavioral_rules())
    assert "Catálogo de productos:" in full


def test_messages_replica_build_payload():
    fx = load_fixture("restaurante")
    caso = fx["casos"][1]  # precio_churrasco: trae historial
    msgs = build_messages(fx, caso)
    assert msgs[0]["role"] == "system"
    assert [m["role"] for m in msgs[1:]] == ["user", "assistant", "user"]
    assert msgs[-1]["content"] == caso["mensaje"]


@pytest.mark.parametrize("raw,esperado", [
    ("8.900", 8900), ("8,900", 8900), ("8900", 8900),
    ("12.500", 12500), ("1.5", None), ("2500.", 2500),
])
def test_parse_monto(raw, esperado):
    assert _parse_monto(raw) == esperado


def test_check_asserts_precio_valido_e_inventado():
    fx = load_fixture("restaurante")
    caso = fx["casos"][1]
    ok = "El Churrasco Italiano cuesta $8.900, ¿te lo preparo?"
    assert check_asserts(ok, fx, caso) == []
    inventado = "El Churrasco Italiano cuesta $8.900 y de postre $9.999"
    fallas = check_asserts(inventado, fx, caso)
    assert any("precio inventado" in f for f in fallas)


def test_check_asserts_must_y_regex():
    fx = load_fixture("peluqueria")
    caso = fx["casos"][0]  # precio_corte
    fallas = check_asserts("Tenemos un plato especial a $25.000", fx, caso)
    assert any("must_not_contain" in f for f in fallas)
    assert check_asserts("El Corte Básico vale $25.000", fx, caso) == []


def test_cost_cap_aborta():
    cap = CostCap(0.001)
    cap.add(1_000_000, 500_000)  # >> cap
    with pytest.raises(RuntimeError, match="CAP DE COSTO"):
        cap.check()
