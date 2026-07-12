"""Fase A (Paso 4) — schema y validación en publicación de tenant.config."""

import pytest
from pydantic import ValidationError

from app.schemas.tenant_config import RubroManifest, TenantConfig, validate_tenant_config
from shared.rubros import PRIMITIVAS, rubro_def, rubros_disponibles
from shared.utils.exceptions import UnprocessableError


class TestTenantConfig:
    def test_acepta_rubro_valido_none_y_extra_keys(self):
        TenantConfig.model_validate({"rubro": "peluqueria"})
        TenantConfig.model_validate({"rubro": None})
        TenantConfig.model_validate({})
        # extra keys (billing/sector/onboarding) se preservan, no se rechazan
        TenantConfig.model_validate({"rubro": "restaurante", "billing": {"x": 1}, "sector": "y"})

    @pytest.mark.parametrize("bad", ["xxx", "peluquria", "RESTAURANTE", ""])
    def test_rechaza_rubro_desconocido(self, bad):
        with pytest.raises(ValidationError):
            TenantConfig.model_validate({"rubro": bad})


class TestValidateTenantConfig:
    def test_noop_en_vacio(self):
        validate_tenant_config(None)
        validate_tenant_config({})

    def test_ok_con_rubro_valido(self):
        validate_tenant_config({"rubro": "veterinaria", "billing": {"plan": "x"}})

    def test_fail_closed_422_en_rubro_invalido(self):
        with pytest.raises(UnprocessableError):
            validate_tenant_config({"rubro": "no_existe"})


class TestRubroManifest:
    def _proj(self, key):
        r = rubro_def(key)
        return dict(
            key=r.key, nombre=r.nombre, emoji=r.emoji, sector=r.sector,
            labels={p: r.labels[p] for p in PRIMITIVAS}, capacidades=list(r.capacidades),
            sub_entidad_label=r.sub_entidad_label, recurso=r.recurso,
            variantes=r.variantes, precio_medida=r.precio_medida,
            categorias_semilla=list(r.categorias_semilla),
        )

    def test_valida_los_101_rubros(self):
        n = 0
        for key in rubros_disponibles():
            RubroManifest(**self._proj(key))
            n += 1
        assert n >= 101

    def test_rechaza_labels_incompletos(self):
        with pytest.raises(ValidationError):
            RubroManifest(key="x", nombre="x", emoji="x", sector="x",
                          labels={"catalogo": "C"}, capacidades=[])
