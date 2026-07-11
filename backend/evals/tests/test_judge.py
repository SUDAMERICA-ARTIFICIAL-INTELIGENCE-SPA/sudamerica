"""E3 — Tests del juez (sin red): parser, agregación, umbral, prompt."""

import pytest

from evals.fixtures import load_fixture
from evals.judge import (
    aggregate,
    build_judge_prompt,
    evalua_umbral,
    load_config,
    parse_judge_json,
)

DIMS = ["exactitud_precios", "tono", "respeto_fsm", "leak_rubro", "fidelidad_catalogo"]


def _score(**over):
    base = {d: 5 for d in DIMS}
    base.update(over)
    return base


def test_parse_judge_json_con_fences():
    raw = '```json\n{"exactitud_precios": 5, "tono": 4, "respeto_fsm": 5, "leak_rubro": 5, "fidelidad_catalogo": 5, "comentario": "ok"}\n```'
    data = parse_judge_json(raw, DIMS)
    assert data["tono"] == 4


def test_parse_judge_json_invalido():
    with pytest.raises(ValueError, match="tono"):
        parse_judge_json('{"exactitud_precios": 5, "tono": 9, "respeto_fsm": 5, "leak_rubro": 5, "fidelidad_catalogo": 5}', DIMS)
    with pytest.raises(ValueError, match="no devolvió JSON"):
        parse_judge_json("no puedo evaluar", DIMS)


def test_aggregate_y_umbral():
    cfg = load_config()
    scores = [_score(), _score(tono=3, leak_rubro=2)]
    ag = aggregate(scores, cfg["dimensiones"])
    assert ag["n"] == 2 and ag["por_dimension"]["leak_rubro"] == 3.5
    assert evalua_umbral(ag, cfg["umbral"]) == []
    ag_malo = aggregate([_score(leak_rubro=1, tono=2)], cfg["dimensiones"])
    fallas = evalua_umbral(ag_malo, cfg["umbral"])
    assert any("leak_rubro" in f for f in fallas)
    assert evalua_umbral(aggregate([], cfg["dimensiones"]), cfg["umbral"]) == ["sin scores"]


def test_build_judge_prompt_contexto():
    fx = load_fixture("carniceria")
    resultado = {
        "caso": "precio_por_kilo",
        "messages": [{"role": "system", "content": "X"},
                     {"role": "user", "content": "¿A cuánto está la carne molida?"}],
        "respuesta": "La Carne Molida está a $12.500 el kilo",
    }
    prompt = build_judge_prompt(fx, resultado)
    assert "Carne Molida: $12500/kg" in prompt
    assert "rubro: carniceria" in prompt
    assert "$12.500 el kilo" in prompt
    assert "[system]" not in prompt  # el system prompt no se filtra al juez
