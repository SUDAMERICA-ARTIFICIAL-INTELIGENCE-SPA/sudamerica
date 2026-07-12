"""Schema de validación de ``tenant.config`` y contrato del ``RubroManifest`` (Fase A).

Convierte la validación del rubro de un fail-safe SILENCIOSO en runtime a un fail-closed
en PUBLICACIÓN: al escribir el config (onboarding / PATCH /tenants/me / PATCH
/admin/tenants/{id}) un ``rubro`` desconocido se rechaza (422) en vez de degradar a
restaurante frente al cliente. Ver ``docs/arquitectura/fase-A-manifiesto.md`` (H-6).

Import puro: solo ``pydantic`` + ``shared.rubros`` (stdlib). No importa fastapi en el top
(la excepción HTTP se importa perezosamente en ``validate_tenant_config``) para que el
schema sea testeable de forma aislada.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from shared.rubros import CAPACIDADES, PRIMITIVAS, rubros_disponibles


class RubroManifest(BaseModel):
    """Proyección validada de un rubro (contrato contractual py↔ts de la Fase A).

    Espejo del export canónico (``shared/rubros/export_manifest.py``). No es la fuente
    de autoría (esa sigue siendo ``diccionario.py``); documenta y valida la forma del
    manifiesto para el test de paridad y la futura migración a tabla BD (Paso 5).
    """

    model_config = ConfigDict(extra="forbid")

    key: str
    nombre: str
    emoji: str
    sector: str
    labels: dict[str, str]
    capacidades: list[str]
    sub_entidad_label: str | None = None
    recurso: bool = False
    variantes: bool = True
    precio_medida: bool = False
    categorias_semilla: list[str] = []

    @field_validator("labels")
    @classmethod
    def _labels_completos(cls, v: dict[str, str]) -> dict[str, str]:
        faltantes = [p for p in PRIMITIVAS if p not in v]
        if faltantes:
            raise ValueError(f"labels incompletos: faltan {faltantes}")
        return v

    @field_validator("capacidades")
    @classmethod
    def _capacidades_conocidas(cls, v: list[str]) -> list[str]:
        # Fase B (Paso 5): la edición en runtime del manifiesto (CRUD admin) valida
        # fail-closed contra el catálogo canónico. Una capacidad fuera de ``CAPACIDADES``
        # (los 22 slugs de ``shared/rubros/capacidades.py``) se rechaza (422): la tabla
        # ``rubros`` nunca queda en un estado que el kernel no sepa gatear. Los 101 rubros
        # seedeados solo usan capacidades del catálogo, así que la paridad del Paso 4 no
        # se debilita.
        desconocidas = [c for c in v if c not in CAPACIDADES]
        if desconocidas:
            raise ValueError(f"capacidades desconocidas: {desconocidas}")
        return v


class TenantConfig(BaseModel):
    """Schema de ``tenant.config``. Valida el ``rubro`` y admite claves extra.

    Se permite ``extra='allow'`` porque ``config`` es un JSONB abierto (billing,
    onboarding, instrucciones_*, sector, …): la Fase A solo garantiza el contrato del
    rubro; el resto se preserva sin tocar.
    """

    model_config = ConfigDict(extra="allow")

    rubro: str | None = None

    @field_validator("rubro")
    @classmethod
    def _rubro_conocido(cls, v: str | None) -> str | None:
        if v is not None and v not in rubros_disponibles():
            raise ValueError(f"rubro desconocido: {v!r}")
        return v


def validate_tenant_config(config: dict | None) -> None:
    """Valida un config de tenant en PUBLICACIÓN (fail-closed).

    Lanza ``shared.utils.exceptions.UnprocessableError`` (→ HTTP 422) si el ``rubro`` es
    inválido. No-op si ``config`` es vacío/None. No muta el config: solo es una puerta.
    """
    if not config:
        return
    try:
        TenantConfig.model_validate(config)
    except ValidationError as exc:
        # Import perezoso: evita acoplar este módulo (testeable con solo pydantic) a fastapi.
        from shared.utils.exceptions import UnprocessableError

        msg = exc.errors()[0].get("msg", "config inválido")
        raise UnprocessableError(f"config de tenant inválido: {msg}") from exc
