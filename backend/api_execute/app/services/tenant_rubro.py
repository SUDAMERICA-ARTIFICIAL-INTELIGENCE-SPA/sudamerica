"""Helper compartido: rubro del tenant desde tenants.config (F5 multi-rubro).

Consolida el patrón repetido de F1/F3 (ai_orchestrator y sudamerica_orchestrator
conservan copias locales; su consolidación es parte de F6).
"""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.rubros import RUBRO_DEFAULT, resolve_rubro

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
        return resolve_rubro(cfg if isinstance(cfg, dict) else None)
    except Exception:
        logger.warning("Could not resolve rubro for tenant %s", tenant_id, exc_info=True)
        return RUBRO_DEFAULT
