"""Helper compartido: rubro del tenant desde tenants.config (F5 multi-rubro).

Consolida el patrón repetido de F1/F3 (ai_orchestrator y sudamerica_orchestrator
conservan copias locales; su consolidación es parte de F6).
"""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.rubros import RUBRO_DEFAULT

# Fase B (Paso 5): la resolución de la clave usa el roster del registro DB-backed (fallback puro a
# diccionario.py). El roster seedeado == el de código → comportamiento idéntico hoy; queda correcto
# si en Paso 6+ un POST añade rubros nuevos que aún no estén en diccionario.py.
from app.services.rubro_registry import resolve_rubro

logger = logging.getLogger(__name__)


async def load_tenant_rubro(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Rubro del tenant desde tenants.config JSON (fail-safe restaurante)."""
    try:
        result = await db.execute(
            text("SELECT config FROM tenants WHERE id = :tid"),
            {"tid": str(tenant_id)},
        )
        cfg = result.scalar_one_or_none()
        if isinstance(cfg, str):
            cfg = json.loads(cfg or "{}")
        cfg = cfg if isinstance(cfg, dict) else None
        resolved = resolve_rubro(cfg)
        # Runtime ya NO degrada en silencio: si el config trae un rubro desconocido
        # (datos legados/corruptos; la publicación es fail-closed) se loggea el fail-safe.
        raw = cfg.get("rubro") if cfg else None
        if isinstance(raw, str) and raw != resolved:
            logger.warning(
                "Rubro desconocido %r en tenant %s; usando fail-safe %r", raw, tenant_id, resolved,
            )
        return resolved
    except Exception:
        logger.warning("Could not resolve rubro for tenant %s", tenant_id, exc_info=True)
        return RUBRO_DEFAULT
