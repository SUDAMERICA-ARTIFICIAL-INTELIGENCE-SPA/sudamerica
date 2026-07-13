"""Servicio del dominio Compras/Proveedores (OLA B). Consultas de lectura + CRUD proveedores."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compras import Proveedor
from shared.utils.exceptions import NotFoundError


async def _count(db: AsyncSession, sql: str, params: dict) -> int:
    return (await db.execute(text(sql), params)).scalar() or 0


# ── Proveedores (con CxP y actividad agregada) ──

async def list_proveedores(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50, search: str | None = None
) -> tuple[list[dict], int]:
    where = "p.tenant_id = :t AND p.activo"
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    if search:
        where += " AND p.nombre ILIKE :q"
        params["q"] = f"%{search}%"
    total = await _count(db, f"SELECT count(*) FROM proveedores p WHERE {where}", params)
    rows = (await db.execute(text(f"""
        SELECT p.*,
          COALESCE(f.cxp, 0) AS cxp,
          COALESCE(f.total_comprado, 0) AS total_comprado,
          COALESCE(o.ordenes_count, 0) AS ordenes_count
        FROM proveedores p
        LEFT JOIN (
          SELECT proveedor_id,
            SUM(CASE WHEN estado NOT IN ('PAGADA','ANULADA') THEN total - monto_pagado ELSE 0 END) AS cxp,
            SUM(total) AS total_comprado
          FROM facturas_proveedor WHERE tenant_id = :t GROUP BY proveedor_id
        ) f ON f.proveedor_id = p.id
        LEFT JOIN (
          SELECT proveedor_id, count(*) AS ordenes_count
          FROM ordenes_compra WHERE tenant_id = :t AND estado <> 'CANCELADA' GROUP BY proveedor_id
        ) o ON o.proveedor_id = p.id
        WHERE {where}
        ORDER BY total_comprado DESC NULLS LAST, p.nombre
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def create_proveedor(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> Proveedor:
    prov = Proveedor(tenant_id=tenant_id, **data)
    db.add(prov)
    await db.flush()
    return prov


async def update_proveedor(db: AsyncSession, tenant_id: uuid.UUID, prov_id: uuid.UUID, data: dict) -> Proveedor:
    from sqlalchemy import select
    row = (await db.execute(
        select(Proveedor).where(Proveedor.id == prov_id, Proveedor.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not row:
        raise NotFoundError("Proveedor", str(prov_id))
    for k, v in data.items():
        if v is not None and hasattr(row, k):
            setattr(row, k, v)
    await db.flush()
    return row


# ── Órdenes de compra ──

async def list_ordenes(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50, estado: str | None = None
) -> tuple[list[dict], int]:
    where = "o.tenant_id = :t"
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    if estado:
        where += " AND o.estado = :estado"
        params["estado"] = estado
    total = await _count(db, f"SELECT count(*) FROM ordenes_compra o WHERE {where}", params)
    rows = (await db.execute(text(f"""
        SELECT o.*, pr.nombre AS proveedor_nombre,
          (SELECT count(*) FROM oc_items WHERE orden_compra_id = o.id) AS items_count
        FROM ordenes_compra o
        JOIN proveedores pr ON pr.id = o.proveedor_id
        WHERE {where}
        ORDER BY o.fecha_emision DESC, o.numero DESC
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def get_orden(db: AsyncSession, tenant_id: uuid.UUID, oc_id: uuid.UUID) -> dict:
    row = (await db.execute(text("""
        SELECT o.*, pr.nombre AS proveedor_nombre
        FROM ordenes_compra o JOIN proveedores pr ON pr.id = o.proveedor_id
        WHERE o.id = :id AND o.tenant_id = :t
    """), {"id": str(oc_id), "t": str(tenant_id)})).mappings().first()
    if not row:
        raise NotFoundError("OrdenCompra", str(oc_id))
    items = (await db.execute(text("""
        SELECT * FROM oc_items WHERE orden_compra_id = :id ORDER BY descripcion
    """), {"id": str(oc_id)})).mappings().all()
    d = dict(row)
    d["items"] = [dict(i) for i in items]
    d["items_count"] = len(d["items"])
    return d


# ── Recepciones ──

async def list_recepciones(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM recepciones WHERE tenant_id = :t", params)
    rows = (await db.execute(text("""
        SELECT r.*, o.numero AS oc_numero, pr.nombre AS proveedor_nombre,
          (SELECT count(*) FROM recepcion_items WHERE recepcion_id = r.id) AS items_count,
          (SELECT COALESCE(SUM(cantidad),0) FROM recepcion_items WHERE recepcion_id = r.id) AS total_unidades
        FROM recepciones r
        JOIN ordenes_compra o ON o.id = r.orden_compra_id
        JOIN proveedores pr ON pr.id = o.proveedor_id
        WHERE r.tenant_id = :t
        ORDER BY r.fecha DESC, r.numero DESC
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


# ── Facturas de proveedor (CxP) ──

async def list_facturas(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50, estado: str | None = None
) -> tuple[list[dict], int]:
    where = "f.tenant_id = :t"
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    if estado:
        where += " AND f.estado = :estado"
        params["estado"] = estado
    total = await _count(db, f"SELECT count(*) FROM facturas_proveedor f WHERE {where}", params)
    rows = (await db.execute(text(f"""
        SELECT f.*, pr.nombre AS proveedor_nombre, (f.total - f.monto_pagado) AS saldo
        FROM facturas_proveedor f JOIN proveedores pr ON pr.id = f.proveedor_id
        WHERE {where}
        ORDER BY f.fecha_emision DESC
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


# ── Requisiciones / Cotizaciones ──

async def list_requisiciones(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM requisiciones WHERE tenant_id = :t", params)
    rows = (await db.execute(text("""
        SELECT * FROM requisiciones WHERE tenant_id = :t
        ORDER BY fecha DESC, numero DESC LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


async def list_cotizaciones(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    params = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    total = await _count(db, "SELECT count(*) FROM cotizaciones WHERE tenant_id = :t", params)
    rows = (await db.execute(text("""
        SELECT c.*, pr.nombre AS proveedor_nombre FROM cotizaciones c
        JOIN proveedores pr ON pr.id = c.proveedor_id
        WHERE c.tenant_id = :t
        ORDER BY c.fecha DESC, c.numero DESC LIMIT :limit OFFSET :offset
    """), params)).mappings().all()
    return [dict(r) for r in rows], total


# ── Evaluación de proveedores (derivada de OC/recepciones) ──

async def evaluacion_proveedores(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    rows = (await db.execute(text("""
        SELECT pr.id AS proveedor_id, pr.nombre, pr.categoria, pr.rating, pr.lead_time_dias,
          COUNT(o.id) FILTER (WHERE o.estado <> 'CANCELADA') AS ordenes_totales,
          COUNT(o.id) FILTER (WHERE o.estado = 'RECIBIDA') AS ordenes_recibidas,
          COALESCE(SUM(o.total) FILTER (WHERE o.estado = 'RECIBIDA'), 0) AS total_comprado
        FROM proveedores pr
        LEFT JOIN ordenes_compra o ON o.proveedor_id = pr.id AND o.tenant_id = :t
        WHERE pr.tenant_id = :t AND pr.activo
        GROUP BY pr.id
        ORDER BY total_comprado DESC
    """), {"t": str(tenant_id)})).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        tot = d["ordenes_totales"] or 0
        rec = d["ordenes_recibidas"] or 0
        # puntualidad: recepciones dentro de la fecha esperada (aproximada por rating base + ratio recibido)
        cumplimiento = (rec / tot * 100) if tot else 0
        # puntualidad determinista a partir del lead time (proxy demo): mejor lead time ⇒ más puntual
        lt = d.get("lead_time_dias") or 10
        puntualidad = max(70.0, min(99.0, 100 - lt * 1.2))
        d["cumplimiento_pct"] = round(cumplimiento, 1)
        d["puntualidad_pct"] = round(puntualidad, 1)
        out.append(d)
    return out


# ── Resumen (KPIs del dominio) ──

async def resumen(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    row = (await db.execute(text("""
        SELECT
          (SELECT count(*) FROM proveedores WHERE tenant_id = :t AND activo) AS proveedores_activos,
          (SELECT COALESCE(SUM(total),0) FROM facturas_proveedor WHERE tenant_id = :t) AS total_comprado_12m,
          (SELECT COALESCE(SUM(total - monto_pagado),0) FROM facturas_proveedor
             WHERE tenant_id = :t AND estado NOT IN ('PAGADA','ANULADA')) AS cxp_total,
          (SELECT COALESCE(SUM(total - monto_pagado),0) FROM facturas_proveedor
             WHERE tenant_id = :t AND estado = 'VENCIDA') AS cxp_vencida,
          (SELECT count(*) FROM ordenes_compra WHERE tenant_id = :t
             AND estado IN ('BORRADOR','ENVIADA','CONFIRMADA','RECIBIDA_PARCIAL')) AS ordenes_abiertas,
          (SELECT count(*) FROM ordenes_compra WHERE tenant_id = :t
             AND date_trunc('month', fecha_emision) = date_trunc('month', CURRENT_DATE)) AS ordenes_mes,
          (SELECT count(*) FROM facturas_proveedor WHERE tenant_id = :t
             AND estado IN ('PENDIENTE','VENCIDA')) AS facturas_pendientes
    """), {"t": str(tenant_id)})).mappings().first()
    return dict(row)
