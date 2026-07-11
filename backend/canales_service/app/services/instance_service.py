"""Service layer for EvolutionInstance — maps WhatsApp instances to tenants."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution_instance import EvolutionInstance
from shared.database import set_tenant_context

logger = logging.getLogger(__name__)


async def register_instance(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    phone_number: str | None = None,
    evo_token: str | None = None,
) -> EvolutionInstance:
    """Create or update an evolution instance row for a tenant (upsert)."""
    values = {
        "tenant_id": tenant_id,
        "instance_name": instance_name,
        "status": "DISCONNECTED",
        "phone_number": phone_number or "",
        "evo_token": evo_token,
        "activo": True,
    }
    stmt = (
        pg_insert(EvolutionInstance)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["instance_name"],
            set_={
                "phone_number": phone_number or "",
                "evo_token": evo_token,
                "status": "DISCONNECTED",
                "activo": True,
            },
        )
        .returning(EvolutionInstance)
    )
    result = await db.execute(stmt)
    instance = result.scalar_one()
    logger.info("Registered instance %s for tenant %s", instance_name, tenant_id)
    return instance


async def lookup_by_instance_name(
    db: AsyncSession,
    instance_name: str,
) -> EvolutionInstance | None:
    """Find an active instance by its name (used by webhook to resolve tenant)."""
    stmt = (
        select(EvolutionInstance)
        .where(
            EvolutionInstance.instance_name == instance_name,
            EvolutionInstance.activo.is_(True),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession,
    instance_name: str,
    status: str,
    phone_number: str | None = None,
) -> EvolutionInstance | None:
    """Update connection status for an instance."""
    instance = await lookup_by_instance_name(db, instance_name)
    if instance is None:
        return None
    await set_tenant_context(db, str(instance.tenant_id))
    instance.status = status
    if phone_number is not None:
        instance.phone_number = phone_number
    await db.flush()
    logger.info("Instance %s status updated to %s", instance_name, status)
    return instance


async def deactivate_instance(
    db: AsyncSession,
    instance_name: str,
) -> EvolutionInstance | None:
    """Soft-delete an instance (set activo=False, status=DISCONNECTED)."""
    instance = await lookup_by_instance_name(db, instance_name)
    if instance is None:
        return None
    await set_tenant_context(db, str(instance.tenant_id))
    instance.activo = False
    instance.status = "DISCONNECTED"
    await db.flush()
    logger.info("Instance %s deactivated", instance_name)
    return instance


async def get_instance_for_tenant(
    db: AsyncSession,
    tenant_id: UUID,
) -> EvolutionInstance | None:
    """Get the active instance for a tenant."""
    stmt = (
        select(EvolutionInstance)
        .where(
            EvolutionInstance.tenant_id == tenant_id,
            EvolutionInstance.activo.is_(True),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
