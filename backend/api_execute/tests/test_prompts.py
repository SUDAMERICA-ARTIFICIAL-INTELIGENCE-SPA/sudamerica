"""Tests for prompts_ai: dynamic prompt construction."""

from app.prompts_ai import (
    CAMPOS_REGISTRO,
    PROMPT_SECTIONS_REGISTRO,
    registro_de_usuarios,
)


def test_registro_no_datos():
    """No data collected yet — all fields should be listed as missing."""
    prompt = registro_de_usuarios()
    assert "Campos que AUN FALTAN" in prompt
    assert "nombre" in prompt
    assert "No se han recopilado datos aun" in prompt


def test_registro_partial_datos():
    """Some fields collected — should show both completed and missing."""
    datos = {"nombre": "Juan", "email": "juan@test.com"}
    prompt = registro_de_usuarios(datos)
    assert "nombre" in prompt
    assert "email" in prompt
    assert "Campos ya recopilados" in prompt
    assert "Campos que AUN FALTAN" in prompt


def test_registro_all_datos():
    """All fields collected — should indicate completion."""
    datos = {campo: f"val_{campo}" for campo in CAMPOS_REGISTRO}
    prompt = registro_de_usuarios(datos)
    assert "TODOS los campos han sido recopilados" in prompt


def test_registro_password_masked():
    """Password field should be masked in the summary."""
    datos = {"password": "secreto123"}
    prompt = registro_de_usuarios(datos)
    assert "secreto123" not in prompt
    assert "********" in prompt


def test_registro_instrucciones_custom():
    """Custom instructions should be appended."""
    prompt = registro_de_usuarios(instrucciones_personalizadas="Habla en ingles")
    assert "Habla en ingles" in prompt


def test_registro_no_instrucciones():
    """Without custom instructions, 'Instrucciones adicionales' should not appear."""
    prompt = registro_de_usuarios()
    assert "Instrucciones adicionales" not in prompt


def test_registro_base_sections_included():
    """All base sections from PROMPT_SECTIONS_REGISTRO should be in the prompt."""
    prompt = registro_de_usuarios()
    for section in PROMPT_SECTIONS_REGISTRO:
        # Each section should be included (at least a significant substring)
        assert section[:30] in prompt


def test_campos_registro_count():
    """All required fields should be defined."""
    assert len(CAMPOS_REGISTRO) == 10
    assert "nombre" in CAMPOS_REGISTRO
    assert "tenant_nombre" in CAMPOS_REGISTRO
    assert "tono" in CAMPOS_REGISTRO


def test_registro_generico_sin_leak_restaurante():
    """F7 M7: el flujo generico pide 'Nombre del negocio'; el default conserva su texto."""
    generico = registro_de_usuarios(rubro="peluqueria")
    assert "Nombre del restaurante o local de comida" not in generico
    assert "tenant_nombre — Nombre del negocio" in generico
    base = registro_de_usuarios()
    assert "tenant_nombre — Nombre del restaurante o local de comida" in base


def test_registro_generico_sin_leak_email_restaurante():
    """R5: el flujo generico pide 'Email del negocio o personal'; el default conserva su texto."""
    generico = registro_de_usuarios(rubro="peluqueria")
    assert "Email del restaurante o personal" not in generico
    assert "Email del negocio o personal" in generico
    base = registro_de_usuarios()
    assert "Email del restaurante o personal" in base
