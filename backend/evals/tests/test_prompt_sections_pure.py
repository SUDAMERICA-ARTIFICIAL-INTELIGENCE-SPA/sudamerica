"""E0 — Fija el system prompt de restaurante construido SOLO con el módulo puro.

Si un test de este archivo falla tras tocar prompt_sections/ai_orchestrator, el
prompt que ve el LLM cambió: correr evals/eval_gate.sh y actualizar el snapshot
solo si el cambio es intencional.
"""

import hashlib

from app.services.prompt_sections import (
    COTIZADOR_RULES,
    DELIVERY_RULES,
    FLOW_CONTROL_RULES,
    INTERACTIVE_MESSAGE_RULES,
    MEDIA_RULES_IMAGES,
    MEDIA_RULES_MENU,
    RESERVA_RULES,
    _format_customer_lines,
    build_catalog_text,
    compose_system_prompt,
)

BASE = "Eres el asistente virtual de Donde Golo. Responde en español."

PRODUCTOS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "nombre": "Churrasco Italiano",
        "precio": 8900,
        "descripcion": "posta, tomate, palta y mayo",
        "disponible": True,
        "imagen_url": "https://x/churrasco.jpg",
        "unidad_venta": "unidad",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "nombre": "Bebida 350cc",
        "precio": 1500,
        "descripcion": None,
        "disponible": False,
        "imagen_url": None,
        "unidad_venta": None,
    },
]

MODIFIERS = {
    "11111111-1111-1111-1111-111111111111": [
        {
            "group_id": "g1",
            "group_nombre": "Agregados",
            "tipo": "MULTI_SELECT",
            "obligatorio": False,
            "mod_id": "m1",
            "mod_nombre": "Extra queso",
            "precio_delta": 800,
            "producto_id": "11111111-1111-1111-1111-111111111111",
        }
    ]
}


def _catalog():
    return build_catalog_text(PRODUCTOS, MODIFIERS)


def test_catalog_text_exact():
    catalog, has_images = _catalog()
    assert has_images is True
    assert catalog == (
        "Catálogo de productos:\n"
        "- Churrasco Italiano: $8900 [FOTO] — posta, tomate, palta y mayo "
        "(ID: 11111111-1111-1111-1111-111111111111)\n"
        "  * Agregados (elegir varios):\n"
        "    - Extra queso: +$800 (ID: m1)\n"
        "- [NO DISPONIBLE] Bebida 350cc: $1500 "
        "(ID: 22222222-2222-2222-2222-222222222222)"
    )


def test_precio_medida_sufijo_kg():
    catalog, _ = build_catalog_text(
        [{"id": "x", "nombre": "Carne Molida", "precio": 12500,
          "descripcion": None, "disponible": True, "imagen_url": None,
          "unidad_venta": "kg"}], {},
    )
    assert "- Carne Molida: $12500/kg (ID: x)" in catalog


def _restaurante_prompt():
    catalog, has_images = _catalog()
    return compose_system_prompt(
        BASE,
        rubro_key="restaurante",
        knowledge="[faq] Horario:\nLun-Dom 12:00-23:00",
        catalog=catalog,
        has_images=has_images,
        config={"instrucciones_disponibilidad": ""},
        has_mesas=True,
        delivery_config="COSTO DE DELIVERY: $2500 para Casa Matriz.",
        customer_context="",
    )


def test_restaurante_composition_order():
    """La composición es EXACTAMENTE base + secciones en el orden de prod."""
    catalog, _ = _catalog()
    expected = "\n\n".join([
        BASE,
        "[faq] Horario:\nLun-Dom 12:00-23:00",
        f"{COTIZADOR_RULES}\n\n{catalog}",
        f"{MEDIA_RULES_MENU}\n\n{MEDIA_RULES_IMAGES}\n\n{INTERACTIVE_MESSAGE_RULES}",
        RESERVA_RULES,
        DELIVERY_RULES,
        "COSTO DE DELIVERY: $2500 para Casa Matriz.",
        FLOW_CONTROL_RULES,
    ])
    assert _restaurante_prompt() == expected


def test_restaurante_snapshot_hash():
    """Byte-identidad del prompt completo de restaurante (constantes incluidas)."""
    digest = hashlib.sha256(_restaurante_prompt().encode("utf-8")).hexdigest()
    assert digest == "274959f6e99c547bf03e326e2b274ea11c4b948e5ddd495dea3fad3ed3f65478", f"prompt cambió: sha256={digest}"


def test_restaurante_sin_glosario():
    assert "GLOSARIO DEL NEGOCIO" not in _restaurante_prompt()


def test_peluqueria_glosario_sin_delivery():
    p = compose_system_prompt(BASE, rubro_key="peluqueria", catalog="Catálogo de productos:\nX")
    assert "GLOSARIO DEL NEGOCIO" in p
    assert "FLUJO DE DELIVERY" not in p


def test_cotizador_no_gastronomico_sin_dine_in_ni_bebidas():
    """R1: rubro sin COMANDAS_KDS no recibe la opción 'Comer aquí' ni el bloque de bebidas."""
    p = compose_system_prompt(BASE, rubro_key="ferreteria", catalog="Catálogo de productos:\nX")
    assert "Comer aquí" not in p
    assert "Sugerencia de Bebidas y Upselling" not in p
    assert "algo para tomar" not in p
    # El resto del cotizador (reglas de precios) sigue presente.
    assert "SOLO usa los precios del catálogo" in p


def test_cotizador_restaurante_conserva_dine_in_y_bebidas():
    """R1: restaurante (COMANDAS_KDS) conserva dine-in y upselling de bebidas."""
    p = compose_system_prompt(BASE, rubro_key="restaurante", catalog="Catálogo de productos:\nX")
    assert "Comer aquí" in p
    assert "Sugerencia de Bebidas y Upselling (OBLIGATORIO):" in p


def test_reserva_generica_sin_mesa_ni_rut_obligatorio():
    """R2: rubro no gastronómico con AGENDA no recibe 'reservar mesa' ni RUT obligatorio."""
    p = compose_system_prompt(
        BASE, rubro_key="peluqueria", catalog="Catálogo de productos:\nX", has_mesas=True,
    )
    assert "Reglas para reservas y citas:" in p
    assert "reservas de mesa" not in p
    assert "reservar mesa" not in p
    assert "RUT (obligatorio)" not in p
    # El bloque JSON de confirmación sigue idéntico (contrato aguas abajo intacto).
    assert '"reserva_confirmada": true' in p


def test_reserva_restaurante_intacta():
    """R2: restaurante conserva RESERVA_RULES exacto (mesa + RUT obligatorio)."""
    p = compose_system_prompt(
        BASE, rubro_key="restaurante", catalog="Catálogo de productos:\nX", has_mesas=True,
    )
    assert "Reglas para reservas de mesa:" in p
    assert "RUT (obligatorio)" in p


def test_media_rules_no_gastronomico_neutral():
    """R3: rubro no gastronómico usa 'catálogo'/'productos', no 'menú del restaurante'/'platos'."""
    p = compose_system_prompt(
        BASE, rubro_key="ferreteria", catalog="Catálogo de productos:\nX", has_images=True,
    )
    assert "menú/carta del restaurante" not in p
    assert "FOTOS DE PLATOS" not in p
    assert "FOTOS DE PRODUCTOS" in p


def test_media_rules_restaurante_intacto():
    """R3: restaurante conserva 'menú/carta del restaurante' y 'FOTOS DE PLATOS'."""
    p = compose_system_prompt(
        BASE, rubro_key="restaurante", catalog="Catálogo de productos:\nX", has_images=True,
    )
    assert "el menú/carta del restaurante" in p
    assert "ENVÍO DE FOTOS DE PLATOS (OBLIGATORIO):" in p


_CLIENTE_VIP = {
    "nombre": "Ana",
    "estado_cliente": "VIP",
    "total_pedidos": 5,
    "total_gastado": 42000,
    "plato_favorito": "Corte Básico",
    "ultima_visita": "2026-06-01",
}


def test_customer_context_restaurante_plato_favorito():
    """R4: restaurante conserva 'Plato favorito' / 'sugiere su plato favorito' (byte-idéntico)."""
    lines = _format_customer_lines(_CLIENTE_VIP, "restaurante")
    joined = "\n".join(lines)
    assert "- Plato favorito: Corte Básico" in joined
    assert "sugiere su plato favorito." in joined


def test_customer_context_generico_producto_favorito():
    """R4: rubro no restaurante usa 'Producto favorito' / 'sugiere su producto favorito'."""
    lines = _format_customer_lines(_CLIENTE_VIP, "peluqueria")
    joined = "\n".join(lines)
    assert "Plato favorito" not in joined
    assert "- Producto favorito: Corte Básico" in joined
    assert "sugiere su producto favorito." in joined


def test_customer_context_default_es_restaurante():
    """R4: sin rubro_key el default sigue siendo restaurante (compat callers)."""
    assert any("Plato favorito" in ln for ln in _format_customer_lines(_CLIENTE_VIP))
