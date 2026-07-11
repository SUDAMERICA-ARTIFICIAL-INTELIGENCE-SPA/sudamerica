"""Tests F1 (IA-primero): glosario de rubro + prompts rubro-aware.

Puros (sin DB): verifican el glosario, la parametrización por rubro de prompts_ai y —
crítico— que el rubro por defecto (restaurante) queda byte-idéntico al comportamiento previo.
"""

from app.prompts_ai import (
    CAMPOS_REGISTRO,
    campos_registro,
    sudamerica_admin_prompt,
    registro_de_usuarios,
)
from app.services.rubro_prompt import (
    build_glosario,
    extract_prompt_generico,
    incluye_capacidad,
)
from shared.rubros import Capacidad


# ── Glosario ──────────────────────────────────────────────────────────────


def test_glosario_peluqueria_usa_su_vocabulario():
    g = build_glosario("peluqueria")
    assert "Peluquería / Barbería" in g
    assert "Servicio" in g
    assert "Cita" in g  # agenda ON
    assert "Silla" in g  # recurso ON
    # No cocina (comandas_kds OFF): instrucción explícita de no hablar de cocina
    assert "No hables de cocina" in g


def test_glosario_ferreteria_sin_agenda_ni_cocina():
    g = build_glosario("ferreteria")
    assert "Artículo" in g
    assert "No hables de cocina" in g  # mesas (cocina/salón) OFF
    # agenda OFF → no debe mencionar la línea de reservas de tiempo
    assert "reservas de tiempo" not in g


def test_glosario_gating_helper():
    assert incluye_capacidad("restaurante", Capacidad.DELIVERY) is True
    assert incluye_capacidad("restaurante", Capacidad.AGENDA) is True
    assert incluye_capacidad("peluqueria", Capacidad.DELIVERY) is False
    assert incluye_capacidad("ferreteria", Capacidad.AGENDA) is False


# ── build_system_message: gates son no-op para restaurante (garantía by-construction) ──


def test_restaurante_tiene_todas_las_capacidades_gated_on():
    """Los gates de RESERVA (AGENDA) y DELIVERY no filtran nada para restaurante."""
    assert incluye_capacidad("restaurante", Capacidad.AGENDA) is True
    assert incluye_capacidad("restaurante", Capacidad.DELIVERY) is True


# ── prompts_ai: default byte-idéntico + variante por rubro ──────────────────


def test_registro_restaurante_es_identico_al_default():
    """El rubro explícito 'restaurante' produce el MISMO prompt que sin rubro (regresión)."""
    datos = {"nombre": "Ana"}
    assert registro_de_usuarios(datos) == registro_de_usuarios(datos, rubro="restaurante")


def test_registro_default_mantiene_campos_gastronomicos():
    prompt = registro_de_usuarios()
    assert "tipo_comida" in prompt
    assert "zona_delivery" in prompt


def test_registro_peluqueria_sin_vocabulario_gastronomico():
    prompt = registro_de_usuarios(rubro="peluqueria")
    assert "tipo_comida" not in prompt
    assert "zona_delivery" not in prompt
    assert "Servicio" in prompt  # del glosario
    assert "Peluquería / Barbería" in prompt


def test_campos_registro_por_rubro():
    assert campos_registro() == CAMPOS_REGISTRO
    assert campos_registro("restaurante") == CAMPOS_REGISTRO
    peluqueria = campos_registro("peluqueria")
    assert "tipo_comida" not in peluqueria
    assert "zona_delivery" not in peluqueria
    assert "horario_atencion" in peluqueria


def test_sudamerica_admin_default_es_restaurante():
    prompt = sudamerica_admin_prompt("La Tarantella", "Ana")
    assert "gestionar\nsu restaurante" in prompt or "su restaurante" in prompt


def test_sudamerica_admin_restaurante_explicito_identico_a_default():
    assert sudamerica_admin_prompt("X", "Y") == sudamerica_admin_prompt("X", "Y", rubro="restaurante")


def test_sudamerica_admin_peluqueria_usa_nombre_de_rubro():
    prompt = sudamerica_admin_prompt("Estilo Chic", "Ana", rubro="peluqueria")
    assert "Peluquería / Barbería" in prompt
    assert "Servicio" in prompt  # glosario inyectado


# ── Fix del leak "restaurante" en el mensaje de registro completo ───────────


def test_registro_completion_generico_no_dice_restaurante():
    """Al completar el registro de un rubro genérico, el resumen dice 'negocio', no 'restaurante'."""
    datos = {c: f"val_{c}" for c in campos_registro("peluqueria")}
    prompt = registro_de_usuarios(datos, rubro="peluqueria")
    assert "TODOS los campos han sido recopilados" in prompt
    assert "resumen del negocio" in prompt
    assert "resumen del restaurante" not in prompt


def test_registro_completion_restaurante_byte_identico():
    """Regresión: el rubro por defecto conserva 'resumen del restaurante'."""
    datos = {c: f"val_{c}" for c in CAMPOS_REGISTRO}
    prompt = registro_de_usuarios(datos)
    assert "resumen del restaurante" in prompt


# ── F1.3: prompt de extracción de catálogo generalizado (menu_import) ───────


def test_extract_prompt_generico_usa_vocabulario_del_rubro():
    p = extract_prompt_generico("peluqueria")
    assert "Peluquería / Barbería" in p
    assert "servicios" in p.lower()  # label catálogo
    # Sin vocabulario gastronómico hardcodeado
    assert "restaurante" not in p.lower()
    assert "plato" not in p.lower()
    # Contrato JSON que el parser downstream espera (nombre/descripcion/precio/categoria)
    assert '"items"' in p
    assert '"precio"' in p
    assert '"categoria"' in p


def test_extract_prompt_generico_ferreteria():
    p = extract_prompt_generico("ferreteria")
    assert "Ferretería / Minimarket" in p
    assert "artículo" in p.lower()  # label ítem
    assert "restaurante" not in p.lower()
