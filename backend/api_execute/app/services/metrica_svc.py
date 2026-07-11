"""Metrica service: SQL aggregation queries for dashboard."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comanda import Comanda
from app.models.comanda import ComandaItem
from app.models.lead import Lead
from app.models.producto import Producto
from app.models.sales_target import SalesTarget
from app.models.venta import Venta


def _resolve_period_window(period: str) -> tuple[datetime, datetime]:
    """Return the active reporting window for day, week, or month views."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "day":
        return day_start, now
    if period == "week":
        return day_start - timedelta(days=6), now
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now


async def get_revenue(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Total revenue and count of ventas."""
    result = await db.execute(
        select(
            func.coalesce(func.sum(Venta.total), 0).label("total_revenue"),
            func.count(Venta.id).label("total_ventas"),
        ).where(Venta.tenant_id == tenant_id, Venta.activo.is_(True))
    )
    row = result.one()
    return {"total_revenue": row.total_revenue, "total_ventas": row.total_ventas}


async def get_por_canal(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """Lead count grouped by canal."""
    result = await db.execute(
        select(Lead.canal, func.count(Lead.id).label("cantidad"))
        .where(Lead.tenant_id == tenant_id, Lead.activo.is_(True))
        .group_by(Lead.canal)
    )
    return [
        {"canal": row.canal or "SIN_CANAL", "cantidad": row.cantidad}
        for row in result.all()
    ]


async def get_por_sector(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """Lead count grouped by sector."""
    result = await db.execute(
        select(Lead.sector, func.count(Lead.id).label("cantidad"))
        .where(Lead.tenant_id == tenant_id, Lead.activo.is_(True))
        .group_by(Lead.sector)
    )
    return [
        {"sector": row.sector or "SIN_SECTOR", "cantidad": row.cantidad}
        for row in result.all()
    ]


async def get_productos_top(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 10,
    period: str | None = None,
) -> list[dict]:
    """Top products by total units sold, optionally filtered by reporting period."""
    query = (
        select(
            Venta.producto_id,
            Producto.nombre,
            func.sum(Venta.cantidad).label("total_vendido"),
            func.sum(Venta.total).label("revenue"),
        )
        .join(Producto, Venta.producto_id == Producto.id)
        .where(Venta.tenant_id == tenant_id, Venta.activo.is_(True))
    )

    if period:
        start, end = _resolve_period_window(period)
        query = query.where(Venta.created_at >= start, Venta.created_at <= end)

    result = await db.execute(
        query.group_by(Venta.producto_id, Producto.nombre)
        .order_by(func.sum(Venta.cantidad).desc(), func.sum(Venta.total).desc())
        .limit(limit)
    )
    return [
        {
            "producto_id": str(row.producto_id),
            "nombre": row.nombre,
            "total_vendido": row.total_vendido,
            "revenue": row.revenue,
        }
        for row in result.all()
    ]


async def get_conversion(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Conversion rate: convertidos / total leads."""
    total_q = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id, Lead.activo.is_(True)
        )
    )
    total_leads = total_q.scalar() or 0

    conv_q = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.activo.is_(True),
            Lead.estado == "CONVERTIDO",
        )
    )
    convertidos = conv_q.scalar() or 0
    tasa = (convertidos / total_leads * 100) if total_leads > 0 else 0.0
    return {
        "total_leads": total_leads,
        "convertidos": convertidos,
        "tasa_conversion": round(tasa, 2),
    }


async def get_leads_por_estado(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Lead count grouped by estado."""
    result = await db.execute(
        select(Lead.estado, func.count(Lead.id).label("cantidad"))
        .where(Lead.tenant_id == tenant_id, Lead.activo.is_(True))
        .group_by(Lead.estado)
    )
    return [
        {"estado": row.estado, "cantidad": row.cantidad}
        for row in result.all()
    ]


async def get_dashboard(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Aggregate KPIs for the executive dashboard."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    ventas_q = await db.execute(
        select(func.coalesce(func.sum(Venta.total), 0)).where(
            Venta.tenant_id == tenant_id,
            Venta.activo.is_(True),
            Venta.created_at >= month_start,
        )
    )
    ventas_mes = float(ventas_q.scalar() or 0)

    periodo = now.strftime("%Y-%m")
    meta_q = await db.execute(
        select(SalesTarget.meta_ventas).where(
            SalesTarget.tenant_id == tenant_id,
            SalesTarget.periodo == periodo,
            SalesTarget.asesor_id.is_(None),
            SalesTarget.activo.is_(True),
        )
    )
    meta_mes = float(meta_q.scalar() or 0)

    leads_q = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.activo.is_(True),
            Lead.created_at >= month_start,
        )
    )
    nuevos_leads = leads_q.scalar() or 0

    conv_data = await get_conversion(db, tenant_id)
    tasa_conversion = conv_data["tasa_conversion"]

    ai_metrics = await _get_ai_performance_metrics(db, tenant_id, month_start)

    return {
        "ventas_mes": ventas_mes,
        "meta_mes": meta_mes,
        "nuevos_leads": nuevos_leads,
        "tasa_conversion": tasa_conversion,
        **ai_metrics,
    }


# ── AI Performance Metrics (real data) ──────────────────────────────────────

# Token cost rate: blended input/output for Gemini 2.5 Flash / OpenAI models
_TOKEN_COST_RATE = 0.000003  # $3 per 1M tokens

# Human agent replacement estimates (conservative LATAM rates)
_HUMAN_MINUTES_PER_CONV = 5  # avg minutes a human spends per WhatsApp conversation
_HUMAN_HOURLY_RATE_USD = 4.0  # LATAM customer service hourly rate


async def _get_ai_performance_metrics(
    db: AsyncSession, tenant_id: uuid.UUID, month_start: datetime,
) -> dict:
    """Compute real AI performance metrics from conversation + review data.

    Groups ai_conversations by lead_id (= 1 conversation per lead),
    LEFT JOINs revision_humana to detect which were auto-resolved.
    """
    try:
        result = await db.execute(
            text(
                "WITH conv AS ("
                "  SELECT c.lead_id,"
                "  COALESCE(SUM(c.tokens_used), 0) AS total_tokens,"
                "  COUNT(*) AS msg_count"
                "  FROM ai_conversations c"
                "  WHERE c.tenant_id = :tid AND c.created_at >= :start"
                "    AND c.lead_id IS NOT NULL"
                "  GROUP BY c.lead_id"
                "), conv_review AS ("
                "  SELECT conv.*,"
                "  CASE WHEN rh.id IS NULL THEN 1 ELSE 0 END AS auto_resolved"
                "  FROM conv LEFT JOIN revision_humana rh"
                "  ON rh.tenant_id = :tid AND rh.lead_id = conv.lead_id"
                "  AND rh.created_at >= :start"
                ") SELECT"
                "  COALESCE(COUNT(*), 0) AS total_conversations,"
                "  COALESCE(SUM(auto_resolved), 0) AS auto_resolved_count,"
                "  COALESCE(SUM(total_tokens), 0) AS total_tokens,"
                "  COALESCE(SUM(msg_count), 0) AS total_messages"
                " FROM conv_review"
            ),
            {"tid": str(tenant_id), "start": month_start},
        )
        row = result.one()
        total_conv = int(row.total_conversations or 0)
        auto_resolved = int(row.auto_resolved_count or 0)
        total_tokens = int(row.total_tokens or 0)
        total_messages = int(row.total_messages or 0)
    except Exception:
        total_conv = auto_resolved = total_tokens = total_messages = 0

    costo_tokens = round(total_tokens * _TOKEN_COST_RATE, 4)
    costo_por_conv = round(costo_tokens / total_conv, 4) if total_conv > 0 else 0.0
    tasa_auto = round((auto_resolved / total_conv) * 100, 1) if total_conv > 0 else 0.0
    horas_ahorradas = round(auto_resolved * (_HUMAN_MINUTES_PER_CONV / 60), 1)
    ahorro_usd = round(
        auto_resolved * (_HUMAN_MINUTES_PER_CONV / 60) * _HUMAN_HOURLY_RATE_USD, 2,
    )
    roi = round(((ahorro_usd - costo_tokens) / costo_tokens) * 100, 1) if costo_tokens > 0 else 0.0

    return {
        "ia_atendidas": total_conv,
        "ia_mensajes": total_messages,
        "ia_auto_resueltas": auto_resolved,
        "ia_tasa_auto_resolucion": tasa_auto,
        "ia_total_tokens": total_tokens,
        "ia_costo_tokens_usd": costo_tokens,
        "ia_costo_por_conversacion": costo_por_conv,
        "ia_horas_ahorradas": horas_ahorradas,
        "ahorro_ia_usd": ahorro_usd,
        "ia_roi": roi,
    }


async def get_operational_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str = "day",
) -> dict:
    """Return real restaurant KPIs for the selected reporting period."""
    start, end = _resolve_period_window(period)

    ventas_result = await db.execute(
        select(
            func.coalesce(func.sum(ComandaItem.subtotal), 0).label("revenue_total"),
            func.coalesce(func.sum(ComandaItem.cantidad), 0).label("items_vendidos"),
        )
        .select_from(Comanda)
        .join(ComandaItem, ComandaItem.comanda_id == Comanda.id)
        .where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado == "ENTREGADO",
            Comanda.entregado_at.is_not(None),
            Comanda.entregado_at >= start,
            Comanda.entregado_at <= end,
        )
    )
    ventas_row = ventas_result.one()
    revenue_total = float(ventas_row.revenue_total or 0)
    items_vendidos = int(ventas_row.items_vendidos or 0)

    pedidos_entregados_q = await db.execute(
        select(func.count(Comanda.id)).where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado == "ENTREGADO",
            Comanda.entregado_at.is_not(None),
            Comanda.entregado_at >= start,
            Comanda.entregado_at <= end,
        )
    )
    pedidos_entregados = int(pedidos_entregados_q.scalar() or 0)

    canceladas_q = await db.execute(
        select(func.count(Comanda.id)).where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado == "CANCELADO",
            Comanda.updated_at >= start,
            Comanda.updated_at <= end,
        )
    )
    comandas_canceladas = int(canceladas_q.scalar() or 0)

    abiertas_q = await db.execute(
        select(func.count(Comanda.id)).where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado.in_(["PENDIENTE", "EN_COCINA", "LISTO"]),
        )
    )
    comandas_abiertas = int(abiertas_q.scalar() or 0)

    ticket_promedio = revenue_total / pedidos_entregados if pedidos_entregados else 0.0

    return {
        "revenue_total": revenue_total,
        "pedidos_entregados": pedidos_entregados,
        "items_vendidos": items_vendidos,
        "ticket_promedio": ticket_promedio,
        "comandas_canceladas": comandas_canceladas,
        "comandas_abiertas": comandas_abiertas,
    }


def _compute_item_margin(precio: float, costo: float) -> float | None:
    """Compute real margin % if cost data exists."""
    if costo and precio > 0:
        return (precio - costo) / precio * 100
    return None


def _compute_classification_thresholds(items: list[dict]) -> tuple[int, float, bool]:
    """Return (median_units, median_margin, has_costs) for menu engineering."""
    units_list = sorted(i["unidades"] for i in items)
    median_units = units_list[len(units_list) // 2]

    has_costs = any(i["real_margin"] is not None for i in items)
    if has_costs:
        margins = [i["real_margin"] for i in items if i["real_margin"] is not None]
        median_margin = sorted(margins)[len(margins) // 2] if margins else 0
    else:
        revenue_list = sorted(i["revenue"] for i in items)
        median_margin = revenue_list[len(revenue_list) // 2]
    return median_units, median_margin, has_costs


def _classify_item(
    item: dict, median_units: int, median_margin: float, has_costs: bool, total_revenue: float
) -> dict:
    """Classify a single menu item into STAR/PUZZLE/PLOWHORSE/DOG."""
    high_pop = item["unidades"] >= median_units
    if has_costs and item["real_margin"] is not None:
        high_margin = item["real_margin"] >= median_margin
        margen_pct = round(item["real_margin"], 2)
    else:
        share = (item["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        high_margin = item["revenue"] >= median_margin
        margen_pct = round(share, 2)

    if high_pop and high_margin:
        clasificacion = "STAR"
    elif not high_pop and high_margin:
        clasificacion = "PUZZLE"
    elif high_pop:
        clasificacion = "PLOWHORSE"
    else:
        clasificacion = "DOG"

    return {
        "producto_id": item["producto_id"],
        "nombre": item["nombre"],
        "categoria": None,
        "unidades_vendidas": item["unidades"],
        "revenue": item["revenue"],
        "margen_pct": margen_pct,
        "clasificacion": clasificacion,
    }


async def get_menu_engineering(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str | None = None,
) -> list[dict]:
    """Menu engineering matrix: Stars, Puzzles, Plowhorses, Dogs."""
    query = (
        select(
            Venta.producto_id, Producto.nombre, Producto.costo, Producto.precio,
            func.sum(Venta.cantidad).label("unidades"),
            func.sum(Venta.total).label("revenue"),
        )
        .join(Producto, Venta.producto_id == Producto.id)
        .where(Venta.tenant_id == tenant_id, Venta.activo.is_(True))
    )
    if period:
        start, end = _resolve_period_window(period)
        query = query.where(Venta.created_at >= start, Venta.created_at <= end)

    result = await db.execute(
        query.group_by(Venta.producto_id, Producto.nombre, Producto.costo, Producto.precio)
    )
    rows = result.all()
    if not rows:
        return []

    items = [
        {
            "producto_id": str(r.producto_id), "nombre": r.nombre,
            "unidades": int(r.unidades), "revenue": float(r.revenue),
            "real_margin": _compute_item_margin(float(r.precio or 0), float(r.costo or 0)),
        }
        for r in rows
    ]

    median_units, median_margin, has_costs = _compute_classification_thresholds(items)
    total_revenue = sum(i["revenue"] for i in items)
    classified = [_classify_item(i, median_units, median_margin, has_costs, total_revenue) for i in items]
    return sorted(classified, key=lambda x: x["revenue"], reverse=True)


async def get_financial_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str = "month",
) -> dict:
    """Financial summary: revenue, COGS, margin, food cost %, ticket promedio."""
    start, end = _resolve_period_window(period)

    # Revenue + COGS from delivered comandas
    result = await db.execute(
        select(
            func.count(func.distinct(Comanda.id)).label("total_ventas"),
            func.coalesce(func.sum(ComandaItem.subtotal), 0).label("revenue"),
            func.coalesce(
                func.sum(ComandaItem.costo_unitario * ComandaItem.cantidad), 0
            ).label("cogs"),
            func.coalesce(func.sum(ComandaItem.cantidad), 0).label("items_vendidos"),
        )
        .select_from(Comanda)
        .join(ComandaItem, ComandaItem.comanda_id == Comanda.id)
        .where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado == "ENTREGADO",
            Comanda.entregado_at.is_not(None),
            Comanda.entregado_at >= start,
            Comanda.entregado_at <= end,
        )
    )
    row = result.one()
    revenue = float(row.revenue or 0)
    cogs = float(row.cogs or 0)
    total_ventas = int(row.total_ventas or 0)
    items_vendidos = int(row.items_vendidos or 0)

    margen_bruto = revenue - cogs
    food_cost_pct = (cogs / revenue * 100) if revenue > 0 else 0.0
    margen_pct = (margen_bruto / revenue * 100) if revenue > 0 else 0.0
    ticket_promedio = revenue / total_ventas if total_ventas > 0 else 0.0

    # Products without cost assigned
    sin_costo_q = await db.execute(
        select(func.count(Producto.id)).where(
            Producto.tenant_id == tenant_id,
            Producto.activo.is_(True),
            Producto.costo.is_(None),
        )
    )
    productos_sin_costo = sin_costo_q.scalar() or 0

    return {
        "total_ventas": total_ventas,
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "margen_bruto": round(margen_bruto, 2),
        "food_cost_pct": round(food_cost_pct, 2),
        "margen_pct": round(margen_pct, 2),
        "ticket_promedio": round(ticket_promedio, 2),
        "items_vendidos": items_vendidos,
        "productos_sin_costo": productos_sin_costo,
        "period": period,
    }


async def get_customer_segmentation(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Customer segmentation by loyalty tier (estado_cliente)."""
    result = await db.execute(
        select(
            Lead.estado_cliente,
            func.count(Lead.id).label("cantidad"),
            func.coalesce(func.sum(Lead.total_gastado), 0).label("total_gastado"),
            func.coalesce(func.avg(Lead.frecuencia_dias), 0).label("avg_frecuencia"),
        )
        .where(Lead.tenant_id == tenant_id, Lead.activo.is_(True))
        .group_by(Lead.estado_cliente)
    )
    return [
        {
            "segmento": row.estado_cliente or "SIN_CLASIFICAR",
            "cantidad": row.cantidad,
            "total_gastado": float(row.total_gastado),
            "avg_frecuencia_dias": round(float(row.avg_frecuencia), 1),
        }
        for row in result.all()
    ]


def _days_since_visit(ultima_visita, today) -> int | None:
    """Compute days since last visit, handling date/datetime/string types."""
    if not ultima_visita:
        return None
    if hasattr(ultima_visita, "date"):
        return (today - ultima_visita.date()).days
    try:
        return (today - ultima_visita).days
    except TypeError:
        return None


def _evaluate_at_risk(row, now) -> dict | None:
    """Return at-risk dict for a row if customer is overdue, else None."""
    days = _days_since_visit(row.ultima_visita, now.date())
    if days is None or days <= (row.frecuencia_dias * 1.5):
        return None
    return {
        "id": str(row.id),
        "nombre": row.nombre,
        "estado_cliente": row.estado_cliente,
        "total_gastado": float(row.total_gastado or 0),
        "plato_favorito": row.plato_favorito,
        "dias_sin_visita": days,
        "frecuencia_esperada": row.frecuencia_dias,
    }


async def get_loyalty_insights(
    db: AsyncSession, tenant_id: uuid.UUID
) -> dict:
    """Loyalty insights: at-risk customers, VIP stats, reactivation candidates."""
    now = datetime.now(timezone.utc)

    # VIP/FRECUENTE count
    vip_q = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.activo.is_(True),
            Lead.estado_cliente.in_(["VIP", "FRECUENTE"]),
        )
    )
    total_vip_frecuente = vip_q.scalar() or 0

    # At-risk: VIP/FRECUENTE customers overdue (ultima_visita > frecuencia_dias * 1.5)
    at_risk_q = await db.execute(
        select(
            Lead.id, Lead.nombre, Lead.estado_cliente,
            Lead.total_gastado, Lead.plato_favorito,
            Lead.ultima_visita, Lead.frecuencia_dias,
        ).where(
            Lead.tenant_id == tenant_id,
            Lead.activo.is_(True),
            Lead.estado_cliente.in_(["VIP", "FRECUENTE"]),
            Lead.ultima_visita.is_not(None),
            Lead.frecuencia_dias.is_not(None),
            Lead.frecuencia_dias > 0,
        )
    )
    at_risk = [
        entry
        for row in at_risk_q.all()
        if (entry := _evaluate_at_risk(row, now)) is not None
    ]

    # Inactive with purchase history (reactivation candidates)
    inactive_q = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.activo.is_(True),
            Lead.estado_cliente == "INACTIVO",
            Lead.total_gastado > 0,
        )
    )
    reactivation_candidates = inactive_q.scalar() or 0

    return {
        "total_vip_frecuente": total_vip_frecuente,
        "at_risk_customers": at_risk[:20],  # limit to top 20
        "at_risk_count": len(at_risk),
        "reactivation_candidates": reactivation_candidates,
    }


async def get_revenue_timeseries(
    db: AsyncSession, tenant_id: uuid.UUID, period: str = "month"
) -> list[dict]:
    """Revenue timeseries for the active day, week, or month window."""
    start, end = _resolve_period_window(period)
    fecha_expr = func.date(Venta.created_at)

    result = await db.execute(
        select(
            fecha_expr.label("fecha"),
            func.coalesce(func.sum(Venta.total), 0).label("revenue"),
        )
        .where(
            Venta.tenant_id == tenant_id,
            Venta.activo.is_(True),
            Venta.created_at >= start,
            Venta.created_at <= end,
        )
        .group_by(fecha_expr)
        .order_by(fecha_expr)
    )

    return [
        {
            "fecha": row.fecha.isoformat() if hasattr(row.fecha, "isoformat") else str(row.fecha),
            "revenue_real": float(row.revenue),
            "revenue_forecast": None,
        }
        for row in result.all()
    ]
