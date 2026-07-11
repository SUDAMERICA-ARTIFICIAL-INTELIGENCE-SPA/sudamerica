"""Tests F6 (sub-entidad + precio por medida): SSOT veterinaria + gating + glosario.

Puros (sin DB). El CRUD de sub-entidades es DB-bound (py_compile + revisión);
aquí se fija el contrato del diccionario y las líneas de prompt.
"""

from app.services.rubro_prompt import build_glosario, incluye_capacidad
from shared.rubros import Capacidad, rubro_def, rubros_disponibles


def test_veterinaria_en_ssot_con_subentidad():
    assert "veterinaria" in rubros_disponibles()
    r = rubro_def("veterinaria")
    assert r.tiene_capacidad(Capacidad.EXPEDIENTES)
    assert r.sub_entidad_label == "Mascota"
    assert r.tiene_capacidad(Capacidad.AGENDA)
    assert not r.tiene_capacidad(Capacidad.MESAS)


def test_subentidad_off_en_rubros_previos():
    for key in ("restaurante", "peluqueria", "ferreteria"):
        r = rubro_def(key)
        assert not r.tiene_capacidad(Capacidad.EXPEDIENTES)
        assert r.sub_entidad_label is None


def test_invariante_label_implica_expedientes():
    # Relajada en Etapa B: hay fichas clínicas sin sub-entidad (kine, podo, quiro…),
    # pero toda sub-entidad etiquetada exige la capacidad `expedientes`.
    for key in rubros_disponibles():
        r = rubro_def(key)
        if r.sub_entidad_label is not None:
            assert r.tiene_capacidad(Capacidad.EXPEDIENTES)


def test_glosario_veterinaria_menciona_mascota():
    g = build_glosario("veterinaria")
    assert "Mascota" in g
    assert "Cita" in g  # agenda ON


def test_glosario_sin_subentidad_no_menciona_mascota():
    assert "Mascota" not in build_glosario("ferreteria")


def test_gating_incluye_capacidad_expedientes():
    assert incluye_capacidad("veterinaria", Capacidad.EXPEDIENTES) is True
    assert incluye_capacidad("restaurante", Capacidad.EXPEDIENTES) is False


def test_precio_medida_flag_con_linea_de_glosario():
    # Rubros a peso/medida (carnicería F7 M5 + escala-100). Nota: el assert viejo
    # ("solo carniceria") quedó roto al escalar a 100 rubros; este fija el set real.
    a_peso = {k for k in rubros_disponibles() if rubro_def(k).precio_medida}
    assert a_peso == {
        "carniceria",
        "verduleria",
        "fruteria",
        "pescaderia",
        "fiambreria",
        "frutos_secos_granel",
        "distribuidora_granos",
    }
    for key in rubros_disponibles():
        if key in a_peso:
            assert "por medida" in build_glosario(key)
        else:
            assert "por medida" not in build_glosario(key)
