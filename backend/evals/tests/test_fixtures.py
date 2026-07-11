"""E1 — Valida esquema de los 5 fixtures y byte-identidad restaurante con snapshot E0."""

import hashlib

import pytest

from evals.fixtures import ARQUETIPOS, build_system_prompt, load_fixture, precios_permitidos

SNAPSHOT_RESTAURANTE = "274959f6e99c547bf03e326e2b274ea11c4b948e5ddd495dea3fad3ed3f65478"


@pytest.mark.parametrize("arquetipo", ARQUETIPOS)
def test_fixture_valido(arquetipo):
    fx = load_fixture(arquetipo)
    assert fx["tenant"]["rubro"] == arquetipo
    assert build_system_prompt(fx)


def test_restaurante_byte_identico_snapshot_e0():
    fx = load_fixture("restaurante")
    digest = hashlib.sha256(build_system_prompt(fx).encode("utf-8")).hexdigest()
    assert digest == SNAPSHOT_RESTAURANTE


def test_glosarios_por_arquetipo():
    assert "GLOSARIO" not in build_system_prompt(load_fixture("restaurante"))
    pelu = build_system_prompt(load_fixture("peluqueria"))
    assert "GLOSARIO DEL NEGOCIO" in pelu and "NO hace delivery" in pelu
    carn = build_system_prompt(load_fixture("carniceria"))
    assert "/kg" in carn and "precio por medida/peso" in carn
    vet = build_system_prompt(load_fixture("veterinaria"))
    assert "Mascota" in vet
    ferr = build_system_prompt(load_fixture("ferreteria"))
    assert "FLUJO DE DELIVERY" in ferr and "sin stock" in ferr


def test_precios_permitidos_restaurante():
    fx = load_fixture("restaurante")
    assert precios_permitidos(fx) == {8900, 1500, 800, 2500}
    caso_kg = load_fixture("carniceria")["casos"][1]
    assert 18750 in precios_permitidos(load_fixture("carniceria"), caso_kg)
