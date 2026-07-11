# evals — Pipeline de evaluación agéntica Sudamérica AI

Evalúa OFFLINE (sin Postgres, sin servicios corriendo) la calidad conversacional del
agente IA por rubro/arquetipo. **Describe al bot actual, no lo cambia**: es el gate de
regresión previo a tocar prompts (`ai_orchestrator.py`, `prompt_sections.py`,
`rubro_prompt.py`, `shared/rubros/diccionario.py`).

## Cómo funciona

- El system prompt se construye con `api_execute/app/services/prompt_sections.py`
  (módulo PURO extraído de `ai_orchestrator.py`; prod delega en él → mismo código,
  mismo prompt) + `BEHAVIORAL_RULES` de ai_dialer extraído por `ast` del fuente.
- Los datos (tenant, catálogo, casos) vienen de fixtures YAML en `evals/fixtures/`.
- El turno se corre contra OpenRouter (modelo barato) y se validan asserts
  deterministas + LLM-as-judge con rúbrica.

## Comandos (python = ~/.local/mempalace-venv/bin/python; NO requiere sqlalchemy)

```bash
cd MVP/backend
PY=~/.local/mempalace-venv/bin/python
# tests puros del pipeline (sin red):
PYTHONPATH=.:api_execute $PY -m pytest evals/tests -q --noconftest -p no:cacheprovider
# harness sin LLM (construye prompts + valida fixtures):
PYTHONPATH=.:api_execute $PY -m evals.harness --dry-run
# gate completo (requiere OPENROUTER_API_KEY en el entorno; cap de costo duro):
bash evals/eval_gate.sh
```

Guardrails: cap `EVAL_MAX_CASES` (default 10) y `EVAL_MAX_USD` (default 0.50);
la key jamás se imprime ni se persiste; `evals/out/` está gitignored.

## Loop cerrado (E5/E6)

```bash
# minería de feedback humano (dump local JSON; default: sample sintético):
PYTHONPATH=.:api_execute $PY -m evals.mine_feedback [--dump dump.json]  # → out/candidatos.yaml
# calibración del umbral de confianza:
PYTHONPATH=.:api_execute $PY -m evals.calibrate [--dump dump.json]      # → out/calibracion.md
```
