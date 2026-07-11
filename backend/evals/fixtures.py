"""E1 — Carga y validación de fixtures dorados por arquetipo (módulo puro).

Cada fixture YAML describe un tenant sintético (rubro, catálogo, knowledge,
delivery) y sus ``casos`` dorados. ``build_system_prompt`` delega en
``prompt_sections`` (el MISMO código que prod) → el prompt offline es el real.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.services.prompt_sections import build_catalog_text, compose_system_prompt

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ARQUETIPOS = ["restaurante", "peluqueria", "ferreteria", "carniceria", "veterinaria"]

_REQUIRED_TOP = {"arquetipo", "tenant", "agente_config", "productos", "casos"}
_REQUIRED_CASO = {"nombre", "mensaje", "asserts"}
_ASSERT_KEYS = {"must_contain", "must_not_contain", "regex", "precios_validos", "precios_extra"}
_REQUIRED_PRODUCTO = {"id", "nombre", "precio", "descripcion", "disponible", "imagen_url", "unidad_venta"}


def load_fixture(arquetipo: str) -> dict:
    """Lee y valida un fixture; falla rápido con mensaje claro (input = frontera)."""
    path = FIXTURES_DIR / f"{arquetipo}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    missing = _REQUIRED_TOP - data.keys()
    if missing:
        raise ValueError(f"{path.name}: faltan claves {sorted(missing)}")
    if data["arquetipo"] != arquetipo:
        raise ValueError(f"{path.name}: arquetipo {data['arquetipo']!r} != {arquetipo!r}")
    if "rubro" not in data["tenant"]:
        raise ValueError(f"{path.name}: tenant.rubro requerido")
    for p in data["productos"]:
        pm = _REQUIRED_PRODUCTO - p.keys()
        if pm:
            raise ValueError(f"{path.name}: producto {p.get('nombre')!r} sin {sorted(pm)}")
    if not data["casos"]:
        raise ValueError(f"{path.name}: sin casos")
    for caso in data["casos"]:
        cm = _REQUIRED_CASO - caso.keys()
        if cm:
            raise ValueError(f"{path.name}: caso {caso.get('nombre')!r} sin {sorted(cm)}")
        extra = caso["asserts"].keys() - _ASSERT_KEYS
        if extra:
            raise ValueError(f"{path.name}: caso {caso['nombre']!r} asserts desconocidos {sorted(extra)}")
        for msg in caso.get("historial", []):
            if msg.get("role") not in ("user", "assistant") or "content" not in msg:
                raise ValueError(f"{path.name}: caso {caso['nombre']!r} historial inválido")
    return data


def build_system_prompt(fx: dict) -> str:
    """System prompt REAL del fixture (mismas funciones puras que usa prod)."""
    catalog, has_images = build_catalog_text(fx["productos"], fx.get("modifiers", {}))
    return compose_system_prompt(
        fx["agente_config"]["system_prompt"],
        rubro_key=fx["tenant"]["rubro"],
        knowledge=fx.get("knowledge", ""),
        catalog=catalog,
        has_images=has_images,
        config=fx["agente_config"],
        has_mesas=fx.get("has_mesas", False),
        delivery_config=fx.get("delivery_config", ""),
        customer_context=fx.get("customer_context", ""),
    )


def precios_permitidos(fx: dict, caso: dict | None = None) -> set[int]:
    """Montos que la IA puede mencionar: catálogo + deltas de modifiers + delivery + extras."""
    allowed = {int(p["precio"]) for p in fx["productos"]}
    for mods in fx.get("modifiers", {}).values():
        allowed.update(abs(int(m["precio_delta"] or 0)) for m in mods)
    if fx.get("delivery_costo"):
        allowed.add(int(fx["delivery_costo"]))
    if caso:
        allowed.update(int(x) for x in caso["asserts"].get("precios_extra", []))
    allowed.discard(0)
    return allowed
