"""E5 — Tests de minería de feedback con el sample sintético (sin red, sin DB)."""

import json

from evals.mine_feedback import SAMPLE_PATH, analiza, candidatos_dorados, clasifica_edicion


def _rows():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_clasifica_edicion():
    assert clasifica_edicion("cuesta $12.000", "cuesta $14.500") == "precio"
    assert clasifica_edicion(
        "Estimado cliente, le saludo cordialmente y quedo atento.",
        "¡Hola! 😊 ¿Qué te gustaría pedir hoy?") == "contenido"
    assert clasifica_edicion("Serían $100 en total hoy mismo",
                             "Serían $100 en total hoy") == "estilo"


def test_analiza_sample():
    resumen = analiza(_rows())
    assert resumen["total"] == 8
    assert resumen["por_accion"] == {"APROBAR": 3, "EDITAR": 3, "RECHAZAR": 2}
    assert resumen["precision_ia"] == 0.375
    # la confianza de lo aprobado debe ser mayor que la de lo rechazado (sanidad)
    assert (resumen["confianza_por_accion"]["APROBAR"]["media"]
            > resumen["confianza_por_accion"]["RECHAZAR"]["media"])
    assert {e["tipo"] for e in resumen["tipos_edicion"]} == {"precio", "contenido"}


def test_candidatos_formato_e1():
    cands = candidatos_dorados(_rows())
    assert len(cands) == 5  # 3 EDITAR + 2 RECHAZAR
    editado = next(c for c in cands if c["nombre"] == "feedback_r3")
    assert editado["tipo_correccion"] == "precio"
    assert editado["respuesta_esperada"].endswith("$14.500")
    assert all("mensaje" in c and "asserts" in c for c in cands)
