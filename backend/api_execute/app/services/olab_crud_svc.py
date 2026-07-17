"""Servicio de dominios chicos de OLA B (B3): devoluciones, plantillas, documentos, campañas."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.olab_crud import Campana, MensajePlantilla


async def _count(db: AsyncSession, sql: str, params: dict) -> int:
    return (await db.execute(text(sql), params)).scalar() or 0


async def list_devoluciones(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM devoluciones WHERE tenant_id = :t", params)
    rows = (await db.execute(text("""
        SELECT d.*, l.nombre AS cliente_nombre FROM devoluciones d
        LEFT JOIN leads l ON l.id = d.lead_id
        WHERE d.tenant_id = :t ORDER BY d.fecha DESC, d.numero DESC
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def list_plantillas(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 100
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM mensaje_plantillas WHERE tenant_id = :t AND activo", params)
    rows = (await db.execute(text("""
        SELECT * FROM mensaje_plantillas WHERE tenant_id = :t AND activo
        ORDER BY categoria, nombre LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def create_plantilla(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> MensajePlantilla:
    row = MensajePlantilla(tenant_id=tenant_id, **data)
    db.add(row)
    await db.flush()
    return row


async def list_documentos(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50, tipo: str | None = None
) -> tuple[list[dict], int]:
    where = "tenant_id = :t AND activo"
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    if tipo:
        where += " AND tipo = :tipo"
        params["tipo"] = tipo
    total = await _count(db, f"SELECT count(*) FROM documentos_archivos WHERE {where}", params)
    rows = (await db.execute(text(f"""
        SELECT * FROM documentos_archivos WHERE {where}
        ORDER BY created_at DESC LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def list_campanas(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM campanas WHERE tenant_id = :t AND activo", params)
    rows = (await db.execute(text("""
        SELECT * FROM campanas WHERE tenant_id = :t AND activo
        ORDER BY fecha_inicio DESC NULLS LAST LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def create_campana(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> Campana:
    row = Campana(tenant_id=tenant_id, estado="BORRADOR", **data)
    db.add(row)
    await db.flush()
    return row
