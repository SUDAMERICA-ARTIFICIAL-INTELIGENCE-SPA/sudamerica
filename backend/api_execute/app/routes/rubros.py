"""Descubrimiento público del set vivo de rubros (Fase C, Paso 6).

El frontend compila un espejo estático del roster de CÓDIGO (``lib/rubros.ts``, verdad-py del
fixture, paridad py↔ts). Pero un rubro ``origen='runtime'`` creado por un admin **no está** en el
fixture: vive solo en BD. Este endpoint expone el **set vivo** (unión de rubros seed+runtime
**activos**) para que la UI de onboarding/registro/admin pueda ofrecer también los runtime sin
esperar un redeploy. El fixture sigue siendo el *baseline de código*; esta API es la *fuente de
verdad del set vivo*.

Lectura GLOBAL (vocabulario de rubro, no dato sensible; ver ``028_rubros_manifest.sql``): sin
auth, igual que el resto de recursos públicos de onboarding. Sirve desde el caché en proceso del
registro (``rubro_registry``), con fallback puro al roster de código si el registro no está
cargado — sin round-trip a BD.
"""

from fastapi import APIRouter

from app.schemas.rubros_publicos import RubroDisponible
from app.services import rubro_registry

router = APIRouter(prefix="/rubros", tags=["rubros"])


@router.get("/disponibles", response_model=list[RubroDisponible])
async def rubros_disponibles() -> list[RubroDisponible]:
    """Set vivo de rubros (seed+runtime activos) con labels/capacidades, ordenado por ``key``."""
    resultado: list[RubroDisponible] = []
    for key in sorted(rubro_registry.rubros_disponibles()):
        r = rubro_registry.rubro_def(key)
        resultado.append(
            RubroDisponible(
                key=r.key,
                nombre=r.nombre,
                emoji=r.emoji,
                sector=r.sector,
                labels=dict(r.labels),
                capacidades=list(r.capacidades),
                sub_entidad_label=r.sub_entidad_label,
                recurso=r.recurso,
                variantes=r.variantes,
                precio_medida=r.precio_medida,
                categorias_semilla=list(r.categorias_semilla),
            )
        )
    return resultado
