"""E3 — LLM-as-judge: puntúa los transcripts de E2 con rúbrica por dimensión.

Una llamada por transcript (modelo barato, mismo CostCap que el harness).
Dimensiones 1-5: exactitud_precios, tono, respeto_fsm, leak_rubro (5 = cero
vocabulario de restaurante en rubros genéricos), fidelidad_catalogo (no inventar).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import sys
from pathlib import Path

import yaml

from evals.fixtures import ARQUETIPOS, load_fixture
from evals.harness import OUT_DIR, CostCap, call_llm

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

JUDGE_PROMPT = """Eres un evaluador estricto de asistentes de WhatsApp para negocios.
Evalúa la RESPUESTA del asistente en la conversación de abajo.

Negocio: {tenant} (rubro: {rubro})
Catálogo REAL (única fuente de precios válida):
{catalogo}

Conversación:
{conversacion}

RESPUESTA A EVALUAR:
{respuesta}

Puntúa de 1 (pésimo) a 5 (perfecto) cada dimensión:
- exactitud_precios: todo precio mencionado existe en el catálogo (o es un total aritméticamente correcto).
- tono: cálido, profesional, conciso, español natural de Chile, formato WhatsApp.
- respeto_fsm: sigue el flujo del negocio (no confirma pedidos/citas sin los datos requeridos, no se salta pasos).
- leak_rubro: 5 = CERO vocabulario de otro rubro (para rubro != restaurante: nada de "plato", "mesa", "cocina", "comanda", "menú"; si rubro = restaurante este eje es 5 salvo vocabulario absurdo).
- fidelidad_catalogo: no inventa productos, servicios ni capacidades que no están en el contexto.

Responde SOLO con JSON válido:
{{"exactitud_precios": N, "tono": N, "respeto_fsm": N, "leak_rubro": N, "fidelidad_catalogo": N, "comentario": "una frase"}}"""


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def build_judge_prompt(fx: dict, resultado: dict) -> str:
    """Prompt del juez para un resultado del harness (messages + respuesta)."""
    catalogo = "\n".join(
        f"- {p['nombre']}: ${p['precio']}" + (f"/{p['unidad_venta']}" if p.get("unidad_venta") not in (None, "unidad") else "")
        for p in fx["productos"]
    )
    conversacion = "\n".join(
        f"[{m['role']}] {m['content']}" for m in resultado["messages"][1:]
    )
    return JUDGE_PROMPT.format(
        tenant=fx["tenant"]["nombre"], rubro=fx["tenant"]["rubro"],
        catalogo=catalogo, conversacion=conversacion, respuesta=resultado["respuesta"],
    )


def parse_judge_json(text: str, dimensiones: list[str]) -> dict:
    """Extrae el JSON del juez (tolera fences ```json); valida dimensiones 1-5."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"juez no devolvió JSON: {text[:200]!r}")
    data = json.loads(match.group(0))
    for dim in dimensiones:
        val = data.get(dim)
        if not isinstance(val, (int, float)) or not 1 <= val <= 5:
            raise ValueError(f"dimensión {dim} inválida: {val!r}")
    return data


def aggregate(scores: list[dict], dimensiones: list[str]) -> dict:
    """Promedio por dimensión + global de una lista de scores."""
    if not scores:
        return {"promedio": 0.0, "por_dimension": {}, "n": 0}
    por_dim = {d: round(sum(s[d] for s in scores) / len(scores), 2) for d in dimensiones}
    return {
        "promedio": round(sum(por_dim.values()) / len(dimensiones), 2),
        "por_dimension": por_dim,
        "n": len(scores),
    }


def evalua_umbral(agregado: dict, umbral: dict) -> list[str]:
    """Lista de violaciones de umbral (vacía = pasa)."""
    fallas = []
    if agregado["n"] == 0:
        return ["sin scores"]
    if agregado["promedio"] < umbral["promedio_min"]:
        fallas.append(f"promedio {agregado['promedio']} < {umbral['promedio_min']}")
    for dim, val in agregado["por_dimension"].items():
        if val < umbral["dimension_min"]:
            fallas.append(f"{dim} {val} < {umbral['dimension_min']}")
    return fallas


def judge_arquetipo(arquetipo: str, *, api_key: str, cap: CostCap, cfg: dict) -> dict:
    fx = load_fixture(arquetipo)
    path = OUT_DIR / f"transcripts_{arquetipo}.json"
    if not path.exists():
        return {"arquetipo": arquetipo, "error": "sin transcripts (correr harness primero)"}
    transcripts = json.loads(path.read_text(encoding="utf-8"))
    scores, detalles = [], []
    for resultado in transcripts["resultados"]:
        if "respuesta" not in resultado:
            continue
        cap.check()
        time.sleep(1.5)  # espaciar llamadas: los modelos baratos de OpenRouter ratelimitean
        data = call_llm(
            [{"role": "user", "content": build_judge_prompt(fx, resultado)}],
            model=cfg["judge_model"], api_key=api_key,
        )
        usage = data.get("usage", {})
        cap.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        score = parse_judge_json(data["choices"][0]["message"]["content"], cfg["dimensiones"])
        scores.append(score)
        detalles.append({"caso": resultado["caso"], **score})
    agregado = aggregate(scores, cfg["dimensiones"])
    return {"arquetipo": arquetipo, "agregado": agregado, "detalles": detalles,
            "umbral_fallas": evalua_umbral(agregado, cfg["umbral"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM-as-judge sobre transcripts de E2")
    parser.add_argument("--arquetipo", choices=ARQUETIPOS, default=None)
    parser.add_argument("--max-usd", type=float,
                        default=float(os.environ.get("EVAL_MAX_USD", 0.50)))
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: falta OPENROUTER_API_KEY en el entorno (no se imprime nunca)")
        return 2
    cfg = load_config()
    cap = CostCap(args.max_usd)
    arquetipos = [args.arquetipo] if args.arquetipo else ARQUETIPOS
    salida, regresion = {}, False
    for arq in arquetipos:
        res = judge_arquetipo(arq, api_key=api_key, cap=cap, cfg=cfg)
        salida[arq] = res
        if "error" in res:
            print(f"{arq}: {res['error']}")
            continue
        ag = res["agregado"]
        estado = "PASA" if not res["umbral_fallas"] else "REGRESIÓN: " + "; ".join(res["umbral_fallas"])
        print(f"{arq}: promedio {ag['promedio']} (n={ag['n']}) — {estado}")
        if res["umbral_fallas"]:
            regresion = True
    (OUT_DIR / "scores.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"costo juez: ~${cap.spent_usd:.4f} (cap ${cap.max_usd})")
    return 1 if regresion else 0


if __name__ == "__main__":
    sys.exit(main())
