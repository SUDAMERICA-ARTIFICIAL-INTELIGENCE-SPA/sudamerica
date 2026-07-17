"""Servicio de lentes derivadas de OLA A (B1). Solo lectura; cero tablas nuevas.

Fuentes:
- cobros/tesorería: comandas (metodo_pago, pago_confirmado) + valor = Σ comanda_items.subtotal + costo_delivery
- flujo de caja: ingresos = ventas.total por mes; egresos = facturas_proveedor.total por mes
- actividad: feed de ventas + leads + comandas + ai_conversations
- kardex (movimientos): ENTRADA = recepcion_items; SALIDA = ventas
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# valor del pedido a partir de sus líneas (comandas no tiene columna total)
_VALOR = "(COALESCE((SELECT SUM(ci.subtotal) FROM comanda_items ci WHERE ci.comanda_id = c.id), 0) + COALESCE(c.costo_delivery, 0))"


async def get_cobros(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    t = {"t": str(tenant_id)}
    por_metodo = (await db.execute(text(f"""
        SELECT COALESCE(c.metodo_pago, 'SIN_MEDIO') AS metodo,
          SUM(CASE WHEN c.pago_confirmado THEN {_VALOR} ELSE 0 END) AS cobrado,
          SUM(CASE WHEN NOT c.pago_confirmado AND c.estado <> 'CANCELADO' THEN {_VALOR} ELSE 0 END) AS pendiente,
          COUNT(*) AS pedidos
        FROM comandas c WHERE c.tenant_id = :t AND c.activo
        GROUP BY COALESCE(c.metodo_pago, 'SIN_MEDIO')
        ORDER BY cobrado DESC
    """), t)).mappings().all()
    totals = (await db.execute(text(f"""
        SELECT
          SUM(CASE WHEN c.pago_confirmado THEN {_VALOR} ELSE 0 END) AS total_cobrado,
          SUM(CASE WHEN NOT c.pago_confirmado AND c.estado <> 'CANCELADO' THEN {_VALOR} ELSE 0 END) AS total_pendiente,
          COUNT(*) FILTER (WHERE c.pago_confirmado) AS pedidos_cobrados,
          COUNT(*) FILTER (WHERE NOT c.pago_confirmado AND c.estado <> 'CANCELADO') AS pedidos_pendientes
        FROM comandas c WHERE c.tenant_id = :t AND c.activo
    """), t)).mappings().first()
    pendientes = (await db.execute(text(f"""
        SELECT c.id AS comanda_id, l.nombre AS cliente, {_VALOR} AS monto,
          c.metodo_pago AS metodo, c.estado, c.created_at AS fecha
        FROM comandas c LEFT JOIN leads l ON l.id = c.cliente_id
        WHERE c.tenant_id = :t AND c.activo AND NOT c.pago_confirmado AND c.estado <> 'CANCELADO'
        ORDER BY c.created_at DESC LIMIT 15
    """), t)).mappings().all()
    return {
        **dict(totals),
        "por_metodo": [dict(r) for r in por_metodo],
        "pendientes_recientes": [dict(r) for r in pendientes],
    }


async def get_tesoreria(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    t = {"t": str(tenant_id)}
    rows = (await db.execute(text(f"""
        SELECT COALESCE(c.metodo_pago, 'SIN_MEDIO') AS metodo,
          SUM({_VALOR}) AS saldo, COUNT(*) AS movimientos
        FROM comandas c
        WHERE c.tenant_id = :t AND c.activo AND c.pago_confirmado
        GROUP BY COALESCE(c.metodo_pago, 'SIN_MEDIO')
        ORDER BY saldo DESC
    """), t)).mappings().all()
    por_metodo = [dict(r) for r in rows]
    saldo_total = sum((r["saldo"] or 0) for r in por_metodo)
    return {"saldo_total": saldo_total, "por_metodo": por_metodo}


async def get_flujo_caja(db: AsyncSession, tenant_id: uuid.UUID, meses: int = 12) -> list[dict]:
    t = {"t": str(tenant_id), "meses": meses}
    rows = (await db.execute(text("""
        WITH periodos AS (
          SELECT to_char(date_trunc('month', CURRENT_DATE) - (n || ' month')::interval, 'YYYY-MM') AS periodo
          FROM generate_series(0, :meses - 1) n
        ),
        ing AS (
          SELECT to_char(date_trunc('month', created_at), 'YYYY-MM') AS periodo, SUM(total) AS ingresos
          FROM ventas WHERE tenant_id = :t AND activo GROUP BY 1
        ),
        egr AS (
          SELECT to_char(date_trunc('month', fecha_emision), 'YYYY-MM') AS periodo, SUM(total) AS egresos
          FROM facturas_proveedor WHERE tenant_id = :t AND estado <> 'ANULADA' GROUP BY 1
        )
        SELECT p.periodo,
          COALESCE(ing.ingresos, 0) AS ingresos,
          COALESCE(egr.egresos, 0) AS egresos,
          COALESCE(ing.ingresos, 0) - COALESCE(egr.egresos, 0) AS neto
        FROM periodos p
        LEFT JOIN ing ON ing.periodo = p.periodo
        LEFT JOIN egr ON egr.periodo = p.periodo
        ORDER BY p.periodo
    """), t)).mappings().all()
    return [dict(r) for r in rows]


async def get_actividad(db: AsyncSession, tenant_id: uuid.UUID, limit: int = 30) -> list[dict]:
    t = {"t": str(tenant_id), "limit": limit}
    rows = (await db.execute(text("""
        (SELECT 'VENTA' AS tipo, COALESCE(p.nombre, 'Venta') AS titulo,
                l.nombre AS subtitulo, v.total AS monto, v.created_at AS fecha
         FROM ventas v LEFT JOIN leads l ON l.id = v.lead_id LEFT JOIN productos p ON p.id = v.producto_id
         WHERE v.tenant_id = :t AND v.activo ORDER BY v.created_at DESC LIMIT :limit)
        UNION ALL
        (SELECT 'LEAD' AS tipo, l.nombre AS titulo, l.canal AS subtitulo, NULL AS monto, l.created_at AS fecha
         FROM leads l WHERE l.tenant_id = :t AND l.activo ORDER BY l.created_at DESC LIMIT :limit)
        UNION ALL
        (SELECT 'CONVERSACION' AS tipo, 'Mensaje de ' || COALESCE(l.nombre, 'cliente') AS titulo,
                a.canal AS subtitulo, NULL AS monto, a.created_at AS fecha
         FROM ai_conversations a LEFT JOIN leads l ON l.id = a.lead_id
         WHERE a.tenant_id = :t AND a.role = 'user' ORDER BY a.created_at DESC LIMIT :limit)
        ORDER BY fecha DESC LIMIT :limit
    """), t)).mappings().all()
    return [dict(r) for r in rows]


async def get_movimientos(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50, tipo: str | None = None
) -> tuple[list[dict], int]:
    t = {"t": str(tenant_id), "limit": page_size, "offset": (page - 1) * page_size}
    base = """
      (SELECT r.fecha::timestamptz AS fecha, 'ENTRADA' AS tipo, ri.descripcion AS producto,
              ri.producto_id, ri.cantidad, ri.costo_unitario, r.numero AS referencia
       FROM recepcion_items ri JOIN recepciones r ON r.id = ri.recepcion_id
       WHERE r.tenant_id = :t)
      UNION ALL
      (SELECT v.created_at AS fecha, 'SALIDA' AS tipo, p.nombre AS producto,
              v.producto_id, v.cantidad, NULL::numeric AS costo_unitario,
              'Venta' AS referencia
       FROM ventas v LEFT JOIN productos p ON p.id = v.producto_id
       WHERE v.tenant_id = :t AND v.activo)
    """
    where = "" if not tipo else f" WHERE tipo = :tipo"
    if tipo:
        t["tipo"] = tipo
    total = (await db.execute(text(f"SELECT count(*) FROM ({base}) m{where}"), t)).scalar() or 0
    rows = (await db.execute(text(f"""
        SELECT * FROM ({base}) m{where}
        ORDER BY fecha DESC LIMIT :limit OFFSET :offset
    """), t)).mappings().all()
    return [dict(r) for r in rows], total
