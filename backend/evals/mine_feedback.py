"""E5 — Minería de feedback humano (revision_humana) desde dump LOCAL.

SOLO lectura de un JSON local (jamás DB prod). Cómo exportar un dump real
(read-only, desde una consola autorizada):
  SELECT id, accion, confianza, mensaje_original, respuesta_ia,
         respuesta_editada, tiempo_revision_ms
  FROM revision_humana WHERE activo = true;  -- exportar como JSON array
Clasifica patrones de rechazo/edición y emite casos dorados candidatos
(formato E1) en evals/out/candidatos.yaml para curación humana.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from evals.harness import OUT_DIR

SAMPLE_PATH = Path(__file__).resolve().parent / "fixtures" / "revision_humana.sample.json"
_MONTOS_RE = re.compile(r"\$\s?[\d][\d.,]*")


def clasifica_edicion(respuesta_ia: str, respuesta_editada: str) -> str:
    """Heurística del TIPO de corrección: precio | contenido | estilo."""
    if _MONTOS_RE.findall(respuesta_ia) != _MONTOS_RE.findall(respuesta_editada):
        return "precio"
    palabras_ia = set(respuesta_ia.lower().split())
    palabras_ed = set(respuesta_editada.lower().split())
    solape = len(palabras_ia & palabras_ed) / max(len(palabras_ia | palabras_ed), 1)
    return "estilo" if solape >= 0.5 else "contenido"


def analiza(rows: list[dict]) -> dict:
    """Patrones agregados del feedback humano."""
    por_accion: dict[str, list[dict]] = {"APROBAR": [], "EDITAR": [], "RECHAZAR": []}
    for r in rows:
        if r["accion"] in por_accion:
            por_accion[r["accion"]].append(r)
    ediciones = [
        {"id": r["id"], "tipo": clasifica_edicion(r["respuesta_ia"], r["respuesta_editada"] or "")}
        for r in por_accion["EDITAR"]
    ]
    def _conf(rows_):  # distribución de confianza por acción (insumo de E6)
        vals = [float(r["confianza"]) for r in rows_ if r.get("confianza") is not None]
        return {"n": len(vals), "min": min(vals), "max": max(vals),
                "media": round(sum(vals) / len(vals), 3)} if vals else {"n": 0}
    n = len(rows)
    aprob = len(por_accion["APROBAR"])
    return {
        "total": n,
        "precision_ia": round(aprob / n, 3) if n else None,
        "por_accion": {k: len(v) for k, v in por_accion.items()},
        "confianza_por_accion": {k: _conf(v) for k, v in por_accion.items()},
        "tipos_edicion": ediciones,
    }


def candidatos_dorados(rows: list[dict]) -> list[dict]:
    """EDITAR/RECHAZAR → casos candidatos formato E1 (curación humana pendiente)."""
    out = []
    for r in rows:
        if r["accion"] == "APROBAR":
            continue
        caso = {
            "nombre": f"feedback_{r['id']}",
            "origen": {"accion": r["accion"], "confianza": r.get("confianza")},
            "historial": [],
            "mensaje": r["mensaje_original"],
            "respuesta_mala": r["respuesta_ia"],
            "asserts": {"precios_validos": True, "must_not_contain": [], "regex": []},
        }
        if r["accion"] == "EDITAR" and r.get("respuesta_editada"):
            caso["respuesta_esperada"] = r["respuesta_editada"]
            caso["tipo_correccion"] = clasifica_edicion(r["respuesta_ia"], r["respuesta_editada"])
        out.append(caso)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minería de feedback revision_humana (dump local)")
    parser.add_argument("--dump", type=Path, default=SAMPLE_PATH,
                        help=f"JSON local (default: sample sintético {SAMPLE_PATH.name})")
    args = parser.parse_args(argv)
    rows = json.loads(args.dump.read_text(encoding="utf-8"))
    resumen = analiza(rows)
    cands = candidatos_dorados(rows)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "candidatos.yaml").write_text(
        yaml.safe_dump({"resumen": resumen, "candidatos": cands},
                       allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"filas: {resumen['total']} | precision_ia: {resumen['precision_ia']} | "
          f"acciones: {resumen['por_accion']} | candidatos: {len(cands)} → evals/out/candidatos.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
