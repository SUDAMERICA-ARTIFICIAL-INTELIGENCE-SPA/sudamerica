#!/bin/bash
# E4 — Gate de regresión del agente IA Sudamérica AI.
# Paso previo OBLIGATORIO a tocar prompts (prompt_sections.py, ai_orchestrator.py,
# rubro_prompt.py, shared/rubros/diccionario.py). exit != 0 => NO mergear.
#
# Uso:  bash evals/eval_gate.sh [--dry-run]
# Env:  EVAL_MAX_CASES (default 3 por arquetipo aquí), EVAL_MAX_USD (default 0.50),
#       EVAL_MODEL, OPENROUTER_API_KEY (si falta, se lee de API_KEYS.txt sin imprimirla).
set -euo pipefail
cd "$(dirname "$0")/.."   # MVP/backend

PY="${PY:-$HOME/.local/mempalace-venv/bin/python}"
export PYTHONPATH=".:api_execute"
export EVAL_MAX_CASES="${EVAL_MAX_CASES:-3}"
export EVAL_MAX_USD="${EVAL_MAX_USD:-0.50}"

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "== eval_gate (dry-run: prompts + fixtures, sin LLM) =="
  "$PY" -m pytest evals/tests -q --noconftest -p no:cacheprovider
  "$PY" -m evals.harness --dry-run
  exit 0
fi

# Key solo en el entorno de este proceso; JAMÁS imprimirla ni pasarla por argv.
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  OPENROUTER_API_KEY="$(sed -n 's/^ *OPENROUTER_API_KEY=//p' /home/code/Proyectos/API_KEYS.txt | head -1)"
  export OPENROUTER_API_KEY
fi
[[ -n "$OPENROUTER_API_KEY" ]] || { echo "ERROR: sin OPENROUTER_API_KEY"; exit 2; }

echo "== eval_gate: tests puros =="
"$PY" -m pytest evals/tests -q --noconftest -p no:cacheprovider

echo "== eval_gate: harness E2 (max ${EVAL_MAX_CASES} casos/arquetipo, cap \$${EVAL_MAX_USD}) =="
"$PY" -m evals.harness

echo "== eval_gate: juez E3 =="
"$PY" -m evals.judge

echo "== eval_gate: PASA =="
