"""E2 — Harness de eval offline: prompt real + turno LLM + asserts deterministas.

Sin DB: el system prompt sale de ``evals.fixtures`` (mismas funciones puras que
prod) y ``BEHAVIORAL_RULES`` se extrae por ``ast`` del fuente de api_execute
(``ai_orchestrator``), sin duplicar texto ni importar módulos DB-bound. El turno
replica el armado de contexto de ``ai_orchestrator`` (override + reglas) y el
payload del LLM (system como primer mensaje).

Guardrails: cap duro de casos (EVAL_MAX_CASES) y costo (EVAL_MAX_USD); la API key
solo se lee del entorno y JAMÁS se imprime.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

from evals.fixtures import ARQUETIPOS, build_system_prompt, load_fixture, precios_permitidos

BACKEND_DIR = Path(__file__).resolve().parent.parent
CHAT_SERVICE_PATH = BACKEND_DIR / "api_execute" / "app" / "services" / "ai_orchestrator.py"
OUT_DIR = Path(__file__).resolve().parent / "out"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat"
# Mismos parámetros que prod (LLM_TEMPERATURE / LLM_MAX_TOKENS)
TEMPERATURE = 0.3
MAX_TOKENS = 1024  # respuestas de eval; prod usa 4096 pero el turno típico es corto
# Precios conservadores USD/token para el cap (deepseek-chat ≈ $0.3/M in, $1.2/M out)
PRICE_IN = 0.5e-6
PRICE_OUT = 2.0e-6

MAX_CASES_DEFAULT = 10
MAX_USD_DEFAULT = 0.50

_PRECIO_RE = re.compile(r"\$\s?([\d][\d.,]*)")


def extract_behavioral_rules(path: Path = CHAT_SERVICE_PATH) -> str:
    """Extrae BEHAVIORAL_RULES del fuente de api_execute sin importarlo (ast)."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "BEHAVIORAL_RULES" for t in node.targets
        ):
            value = node.value
            # Forma en prod: """...""".strip()
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "strip"
                and isinstance(value.func.value, ast.Constant)
            ):
                return value.func.value.value.strip()
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
    raise RuntimeError(f"BEHAVIORAL_RULES no encontrado en {path}")


def build_full_system_prompt(fx: dict) -> str:
    """Prompt COMPLETO que ve el LLM: override de api_execute + BEHAVIORAL_RULES.

    Réplica de ``ai_orchestrator``: ``system_prompt_override + "\\n\\n" + BEHAVIORAL_RULES``.
    """
    return build_system_prompt(fx) + "\n\n" + extract_behavioral_rules()


def build_messages(fx: dict, caso: dict) -> list[dict]:
    """Réplica de ``llm_service._build_payload``: system primero, luego historial, luego user."""
    return [
        {"role": "system", "content": build_full_system_prompt(fx)},
        *[{"role": m["role"], "content": m["content"]} for m in caso.get("historial", [])],
        {"role": "user", "content": caso["mensaje"]},
    ]


def _parse_monto(raw: str) -> int | None:
    """"8.900" / "8,900" / "8900" → 8900. Ignora decimales tipo "1.5"."""
    cleaned = raw.rstrip(".,")
    digits = cleaned.replace(".", "").replace(",", "")
    if not digits.isdigit():
        return None
    # "1.5" es cantidad, no precio de miles: solo separador de miles válido (grupos de 3)
    if ("." in cleaned or "," in cleaned) and not re.fullmatch(r"\d{1,3}([.,]\d{3})+", cleaned):
        return None
    return int(digits)


def check_asserts(respuesta: str, fx: dict, caso: dict) -> list[str]:
    """Asserts deterministas del caso; retorna lista de fallas (vacía = OK)."""
    fallas: list[str] = []
    a = caso["asserts"]
    baja = respuesta.lower()
    for s in a.get("must_contain", []):
        if s.lower() not in baja:
            fallas.append(f"must_contain falta: {s!r}")
    for s in a.get("must_not_contain", []):
        if s.lower() in baja:
            fallas.append(f"must_not_contain presente: {s!r}")
    for rx in a.get("regex", []):
        if not re.search(rx, respuesta):
            fallas.append(f"regex sin match: {rx!r}")
    if a.get("precios_validos"):
        permitidos = precios_permitidos(fx, caso)
        for raw in _PRECIO_RE.findall(respuesta):
            monto = _parse_monto(raw)
            if monto is not None and monto not in permitidos:
                fallas.append(f"precio inventado: ${raw} (permitidos: {sorted(permitidos)})")
    return fallas


class CostCap:
    """Cap duro de gasto acumulado por corrida (guardrail ≤ EVAL_MAX_USD)."""

    def __init__(self, max_usd: float):
        self.max_usd = max_usd
        self.spent_usd = 0.0

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.spent_usd += prompt_tokens * PRICE_IN + completion_tokens * PRICE_OUT

    def check(self) -> None:
        if self.spent_usd >= self.max_usd:
            raise RuntimeError(
                f"CAP DE COSTO alcanzado: ~${self.spent_usd:.3f} >= ${self.max_usd} — abortando"
            )


def call_llm(messages: list[dict], *, model: str, api_key: str, timeout: float = 60.0) -> dict:
    """POST a OpenRouter (retries en 429/5xx, patrón llm_service._post_with_retries)."""
    payload = {"model": model, "messages": messages,
               "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last = None
    for attempt in range(5):
        resp = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=timeout)
        if resp.status_code in (429, 500, 502, 503):
            last = resp.status_code
            retry_after = float(resp.headers.get("Retry-After", 0) or 0)
            time.sleep(max(2.0 * (attempt + 1), retry_after))
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"OpenRouter agotó reintentos (último status {last})")


def run_arquetipo(arquetipo: str, *, model: str, api_key: str | None,
                  max_cases: int, cap: CostCap, dry_run: bool) -> dict:
    fx = load_fixture(arquetipo)
    casos = fx["casos"][:max_cases]
    resultados = []
    for caso in casos:
        messages = build_messages(fx, caso)
        for rx in caso["asserts"].get("regex", []):
            re.compile(rx)  # valida temprano
        if dry_run:
            resultados.append({"caso": caso["nombre"], "dry_run": True,
                               "prompt_chars": len(messages[0]["content"])})
            continue
        cap.check()
        data = call_llm(messages, model=model, api_key=api_key)
        usage = data.get("usage", {})
        cap.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        respuesta = data["choices"][0]["message"]["content"]
        fallas = check_asserts(respuesta, fx, caso)
        resultados.append({"caso": caso["nombre"], "messages": messages,
                           "respuesta": respuesta, "fallas": fallas, "usage": usage})
    return {"arquetipo": arquetipo, "model": model, "resultados": resultados}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness de eval offline Sudamérica AI")
    parser.add_argument("--arquetipo", choices=ARQUETIPOS, default=None,
                        help="uno solo (default: los 5)")
    parser.add_argument("--max-cases", type=int,
                        default=int(os.environ.get("EVAL_MAX_CASES", MAX_CASES_DEFAULT)))
    parser.add_argument("--max-usd", type=float,
                        default=float(os.environ.get("EVAL_MAX_USD", MAX_USD_DEFAULT)))
    parser.add_argument("--model", default=os.environ.get("EVAL_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dry-run", action="store_true",
                        help="construye prompts y valida asserts sin llamar al LLM")
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not args.dry_run and not api_key:
        print("ERROR: falta OPENROUTER_API_KEY en el entorno (no se imprime nunca)")
        return 2

    cap = CostCap(args.max_usd)
    arquetipos = [args.arquetipo] if args.arquetipo else ARQUETIPOS
    total_fallas = 0
    OUT_DIR.mkdir(exist_ok=True)
    for arq in arquetipos:
        res = run_arquetipo(arq, model=args.model, api_key=api_key,
                            max_cases=args.max_cases, cap=cap, dry_run=args.dry_run)
        out_path = OUT_DIR / f"transcripts_{arq}.json"
        if not args.dry_run:
            out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        fallas_arq = sum(len(r.get("fallas", [])) for r in res["resultados"])
        total_fallas += fallas_arq
        estado = "DRY" if args.dry_run else ("OK" if fallas_arq == 0 else f"{fallas_arq} FALLAS")
        print(f"{arq}: {len(res['resultados'])} casos — {estado}")
    if not args.dry_run:
        print(f"costo estimado corrida: ~${cap.spent_usd:.4f} (cap ${cap.max_usd})")
    return 1 if total_fallas else 0


if __name__ == "__main__":
    sys.exit(main())
