"""E6 — Calibración del umbral de confianza (default 0.85) con datos de E5.

Con un dump local de revision_humana: para cada umbral candidato, si el sistema
hubiese auto-enviado todo lo con confianza >= umbral, ¿qué precisión (auto-enviadas
que el humano APROBÓ) y qué cobertura (fracción auto-enviada) habría tenido?

HALLAZGO DOCUMENTADO (investigación 2026-07-02): en la ruta actual con
system_prompt_override, ai_dialer HARDCODEA confianza = 0.95
(AI_dialer/app/services/chat_service.py:1225) → el umbral configurable
agente_config.umbral_confianza (0.85) nunca gatilla revisión: TODO se auto-envía.
La calibración solo tendrá efecto real cuando la confianza vuelva a ser una señal.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evals.harness import OUT_DIR
from evals.mine_feedback import SAMPLE_PATH

UMBRALES = [round(0.5 + 0.05 * i, 2) for i in range(10)]  # 0.50..0.95


def curva(rows: list[dict], umbrales: list[float] = UMBRALES) -> list[dict]:
    """Precisión/cobertura simulada por umbral. APROBAR = la IA estaba correcta."""
    datos = [(float(r["confianza"]), r["accion"] == "APROBAR")
             for r in rows if r.get("confianza") is not None]
    total = len(datos)
    puntos = []
    for u in umbrales:
        auto = [(c, ok) for c, ok in datos if c >= u]
        correctas = sum(1 for _, ok in auto if ok)
        puntos.append({
            "umbral": u,
            "auto_enviadas": len(auto),
            "cobertura": round(len(auto) / total, 3) if total else None,
            "precision": round(correctas / len(auto), 3) if auto else None,
        })
    return puntos


def recomendacion(puntos: list[dict], precision_min: float = 0.9) -> dict | None:
    """Umbral más bajo (max cobertura) cuya precisión simulada >= precision_min."""
    validos = [p for p in puntos if p["precision"] is not None and p["precision"] >= precision_min]
    return min(validos, key=lambda p: p["umbral"]) if validos else None


def render_md(puntos: list[dict], reco: dict | None, fuente: str) -> str:
    filas = "\n".join(
        f"| {p['umbral']:.2f} | {p['auto_enviadas']} | {p['cobertura']} | {p['precision']} |"
        for p in puntos
    )
    reco_txt = (
        f"**Umbral recomendado: {reco['umbral']:.2f}** (precisión simulada {reco['precision']}, "
        f"cobertura {reco['cobertura']})." if reco
        else "**Sin umbral recomendable** con estos datos (precisión < 0.9 en todos)."
    )
    return f"""# Calibración del umbral de confianza (E6)

Fuente de datos: `{fuente}` (dump local read-only de revision_humana).

## ⚠️ Contexto crítico
En la ruta de chat actual (api_execute → ai_dialer con `system_prompt_override`),
la confianza está **hardcodeada en 0.95** (`AI_dialer/app/services/chat_service.py:1225`),
por encima del umbral default 0.85 (`agente_config.umbral_confianza`) → **toda
respuesta se auto-envía y la revisión humana por confianza nunca se gatilla**.
Esta calibración aplica al clasificador real (ruta sin override) y como diseño
objetivo para cuando la confianza vuelva a ser señal (candidato: backlog aparte).

## Curva precisión / cobertura por umbral

| Umbral | Auto-enviadas | Cobertura | Precisión |
|---|---|---|---|
{filas}

{reco_txt}

Regenerar: `PYTHONPATH=.:api_execute $PY -m evals.calibrate [--dump ruta.json]`
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibración del umbral de confianza")
    parser.add_argument("--dump", type=Path, default=SAMPLE_PATH)
    parser.add_argument("--precision-min", type=float, default=0.9)
    args = parser.parse_args(argv)
    rows = json.loads(args.dump.read_text(encoding="utf-8"))
    puntos = curva(rows)
    reco = recomendacion(puntos, args.precision_min)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "calibracion.md").write_text(
        render_md(puntos, reco, args.dump.name), encoding="utf-8")
    print(f"puntos: {len(puntos)} | recomendado: {reco['umbral'] if reco else None} "
          f"→ evals/out/calibracion.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
