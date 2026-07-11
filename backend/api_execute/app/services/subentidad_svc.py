"""Servicio de sub-entidades del cliente (F6 multi-rubro)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subentidad import ClienteSubentidad
from shared.services import crud


async def list_subentidades(
    db: AsyncSession, tenant_id: uuid.UUID, lead_id: uuid.UUID | None = None
) -> list[ClienteSubentidad]:
    query = select(ClienteSubentidad).where(
        ClienteSubentidad.tenant_id == tenant_id,
        ClienteSubentidad.activo.is_(True),
    )
    if lead_id:
        query = query.where(ClienteSubentidad.lead_id == lead_id)
    rows = (await db.execute(query.order_by(ClienteSubentidad.created_at))).scalars().all()
    return list(rows)


async def create_subentidad(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> ClienteSubentidad:
    row = ClienteSubentidad(tenant_id=tenant_id, **data)
    db.add(row)
    await db.flush()
    return row


async def update_subentidad(
    db: AsyncSession, tenant_id: uuid.UUID, subentidad_id: uuid.UUID, data: dict
) -> ClienteSubentidad:
    return await crud.update_fields(
        db, ClienteSubentidad, tenant_id, subentidad_id, data, label="Subentidad"
    )


async def delete_subentidad(
    db: AsyncSession, tenant_id: uuid.UUID, subentidad_id: uuid.UUID
) -> ClienteSubentidad:
    return await crud.update_fields(
        db, ClienteSubentidad, tenant_id, subentidad_id, {"activo": False}, label="Subentidad"
    )
