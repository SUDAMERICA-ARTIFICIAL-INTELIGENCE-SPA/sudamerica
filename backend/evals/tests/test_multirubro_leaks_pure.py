"""Fase A (Paso 4) — Oráculo puro de cierre de fugas restaurante-céntricas.

Complementa ``test_prompt_sections_pure.py`` (snapshot byte-idéntico de la composición
del prompt de cliente) cubriendo las fugas §3.A gateadas en Paso 4:

  - reglas de bienvenida WhatsApp/mesa (``prompt_sections``),
  - copiloto admin ``_SUDAMERICA_*`` (``prompts_ai``).

Doble red: (1) **restaurante byte-idéntico** (las funciones gateadas devuelven la
constante exacta); (2) **rubros no gastronómicos SIN las secciones restaurante-céntricas**.
Puro: solo ``shared.rubros`` + stdlib (no ORM/DB); corre con cualquier Python.
"""

from app.prompts_ai import (
    _SUDAMERICA_CAPABILITIES,
    _SUDAMERICA_EXAMPLES,
    _SUDAMERICA_RULES,
    sudamerica_admin_prompt,
)
from app.services.prompt_sections import (
    WELCOME_RULES_MESA,
    WELCOME_RULES_WHATSAPP,
    welcome_rules_mesa,
    welcome_rules_whatsapp,
)

# Rubros no gastronómicos usados como testigos (sin capacidad ``mesas``).
NO_GASTRO = ["peluqueria", "ferreteria", "inmobiliaria", "veterinaria"]

# Frases restaurante-céntricas que NO deben aparecer en un rubro no gastronómico.
RESTAURANT_ONLY = [
    "Ordenes de cocina",
    "EN_COCINA",
    "Reservar mesa",       # poll de bienvenida whatsapp
    "Ver el menú",         # poll de bienvenida whatsapp
    "mesas del restaurante",
    "sentado en su mesa",
    "Llamar al mesero",
    "Pedir la cuenta",
    "mesero virtual",
    "buen provecho",
    "consultar_disponibilidad_mesas",  # tool mesa-específica
]


# ── Byte-identidad de restaurante ────────────────────────────────────


def test_welcome_whatsapp_restaurante_byte_identico():
    assert welcome_rules_whatsapp("restaurante") == WELCOME_RULES_WHATSAPP


def test_welcome_mesa_restaurante_byte_identico():
    assert welcome_rules_mesa("restaurante") == WELCOME_RULES_MESA


def test_admin_restaurante_byte_identico():
    expected = "\n\n".join([
        ("Eres Sudamérica AI, el copiloto administrativo de Donde Golo. "
         "Tu rol es ayudar a Ana a gestionar su restaurante de forma inteligente y basada en datos."),
        _SUDAMERICA_CAPABILITIES,
        _SUDAMERICA_RULES,
        _SUDAMERICA_EXAMPLES,
    ])
    assert sudamerica_admin_prompt("Donde Golo", "Ana", rubro="restaurante") == expected
    # rubro=None (tenant sin rubro) resuelve al mismo prompt que restaurante.
    assert sudamerica_admin_prompt("Donde Golo", "Ana", rubro=None) == expected


# ── Rubros no gastronómicos sin fugas ────────────────────────────────


def test_welcome_whatsapp_no_gastro_sin_fugas():
    for key in NO_GASTRO:
        p = welcome_rules_whatsapp(key)
        for frase in RESTAURANT_ONLY:
            assert frase not in p, f"[{key}] welcome whatsapp filtró: {frase!r}"


def test_welcome_mesa_no_gastro_sin_fugas():
    for key in NO_GASTRO:
        p = welcome_rules_mesa(key)
        for frase in ("Llamar al mesero", "Pedir la cuenta", "mesero virtual", "buen provecho",
                      "sentado en su mesa"):
            assert frase not in p, f"[{key}] welcome mesa filtró: {frase!r}"


def test_admin_no_gastro_sin_secciones_restaurante():
    for key in NO_GASTRO:
        p = sudamerica_admin_prompt("Negocio", "User", rubro=key)
        for frase in RESTAURANT_ONLY:
            assert frase not in p, f"[{key}] admin filtró: {frase!r}"


def test_peluqueria_welcome_usa_su_vocabulario():
    """Peluquería (AGENDA, sin DELIVERY/MESAS) ofrece 'Reservar Cita', no 'Reservar mesa'."""
    p = welcome_rules_whatsapp("peluqueria")
    assert "Reservar Cita" in p
    assert "Delivery" not in p  # sin capacidad delivery


def test_inmobiliaria_admin_sin_bloques_gastronomicos():
    """Inmobiliaria (sin PEDIDOS/MESAS) no ve los bloques COMANDAS ni MESAS del copiloto."""
    p = sudamerica_admin_prompt("Propiedades Sur", "Luis", rubro="inmobiliaria")
    assert "crear_mesa" not in p
    assert "cambiar_estado_comanda" not in p
    # Conserva lo genérico (ventas/clientes/métricas).
    assert "consultar_ventas" in p
    assert "consultar_clientes" in p
