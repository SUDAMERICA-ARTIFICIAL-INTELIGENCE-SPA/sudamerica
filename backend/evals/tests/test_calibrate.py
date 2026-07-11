"""E6 — Tests de calibración con el sample sintético."""

import json

from evals.calibrate import curva, recomendacion, render_md
from evals.mine_feedback import SAMPLE_PATH


def _rows():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_curva_monotona_en_cobertura():
    puntos = curva(_rows())
    coberturas = [p["cobertura"] for p in puntos]
    assert coberturas == sorted(coberturas, reverse=True)
    # umbral 0.90: solo r1(0.95 APROBAR) y r2(0.91 APROBAR) → precisión 1.0
    p90 = next(p for p in puntos if p["umbral"] == 0.9)
    assert p90["auto_enviadas"] == 2 and p90["precision"] == 1.0
    # umbral 0.50: entra todo (8) → precisión = precision_ia global 0.375
    p50 = next(p for p in puntos if p["umbral"] == 0.5)
    assert p50["auto_enviadas"] == 8 and p50["precision"] == 0.375


def test_recomendacion_y_md():
    puntos = curva(_rows())
    reco = recomendacion(puntos, precision_min=0.9)
    assert reco is not None and reco["precision"] >= 0.9
    md = render_md(puntos, reco, "sample.json")
    assert "hardcodeada en 0.95" in md and "chat_service.py:1225" in md
    assert f"{reco['umbral']:.2f}" in md
