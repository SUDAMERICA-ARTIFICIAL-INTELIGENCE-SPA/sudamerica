"""Metricas routes: dashboard, revenue, operativo, reporting breakdowns."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

from app.routes.deps import MetricasReader
from app.schemas.metrica import (
    CustomerSegment,
    DashboardKpis,
    FinancialSummary,
    LoyaltyInsights,
    MenuEngineeringItem,
    MetricaConversion,
    MetricaLeadEstado,
    MetricaOperativa,
    MetricaPorCanal,
    MetricaPorSector,
    MetricaProductoTop,
    MetricaRevenue,
    RevenueDataPoint,
    WeeklyActivityPoint,
)
from app.schemas.lentes import CobrosResumen, FlujoPunto, ActividadItem, Tesoreria
from app.services import ai_conversation_svc, lentes_svc, metrica_svc

router = APIRouter(prefix="/metricas", tags=["metricas"])


@router.get("/dashboard", response_model=DashboardKpis)
async def dashboard(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Aggregate KPIs for the executive dashboard."""
    return await metrica_svc.get_dashboard(db, current_user["tenant_id"])


@router.get("/operativo", response_model=MetricaOperativa)
async def operativo(
    period: str = Query("day", description="day, week, or month"),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Restaurant KPIs for the selected reporting period."""
    return await metrica_svc.get_operational_summary(
        db,
        current_user["tenant_id"],
        period,
    )


@router.get("/revenue", response_model=MetricaRevenue | list[RevenueDataPoint])
async def revenue(
    period: str | None = Query(None, description="day, week, or month"),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Total revenue or timeseries (when period param is given)."""
    if period:
        return await metrica_svc.get_revenue_timeseries(
            db, current_user["tenant_id"], period
        )
    return await metrica_svc.get_revenue(db, current_user["tenant_id"])


@router.get("/por-canal", response_model=list[MetricaPorCanal])
async def por_canal(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Leads grouped by canal."""
    return await metrica_svc.get_por_canal(db, current_user["tenant_id"])


@router.get("/por-sector", response_model=list[MetricaPorSector])
async def por_sector(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Leads grouped by sector."""
    return await metrica_svc.get_por_sector(db, current_user["tenant_id"])


@router.get("/productos-top", response_model=list[MetricaProductoTop])
async def productos_top(
    period: str | None = Query(None, description="day, week, or month"),
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Top products by units sold."""
    return await metrica_svc.get_productos_top(
        db,
        current_user["tenant_id"],
        limit=limit,
        period=period,
    )


@router.get("/conversion", response_model=MetricaConversion)
async def conversion(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Lead conversion rate."""
    return await metrica_svc.get_conversion(db, current_user["tenant_id"])


@router.get("/leads-estado", response_model=list[MetricaLeadEstado])
async def leads_estado(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Leads grouped by estado."""
    return await metrica_svc.get_leads_por_estado(db, current_user["tenant_id"])


@router.get("/financiero", response_model=FinancialSummary)
async def financial_summary(
    period: str = Query("month", description="day, week, or month"),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Financial summary: revenue, COGS, margin, food cost %."""
    return await metrica_svc.get_financial_summary(
        db, current_user["tenant_id"], period=period
    )


@router.get("/segmentacion-clientes", response_model=list[CustomerSegment])
async def segmentacion_clientes(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Customer segmentation by loyalty tier."""
    return await metrica_svc.get_customer_segmentation(
        db, current_user["tenant_id"]
    )


@router.get("/loyalty-insights", response_model=LoyaltyInsights)
async def loyalty_insights(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Loyalty insights: at-risk customers, VIP stats."""
    return await metrica_svc.get_loyalty_insights(
        db, current_user["tenant_id"]
    )


@router.get("/menu-engineering", response_model=list[MenuEngineeringItem])
async def menu_engineering(
    period: str | None = Query(None, description="day, week, or month"),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Menu engineering matrix (Stars, Puzzles, Plowhorses, Dogs)."""
    return await metrica_svc.get_menu_engineering(
        db, current_user["tenant_id"], period=period
    )


@router.get("/weekly-activity", response_model=list[WeeklyActivityPoint])
async def weekly_activity(
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Conversation activity breakdown by day of week (last 7 days)."""
    return await ai_conversation_svc.get_weekly_activity(
        db, current_user["tenant_id"]
    )


# ── Lentes derivadas de OLA A (B1) ──

@router.get("/cobros", response_model=CobrosResumen)
async def cobros(current_user: dict = MetricasReader, db: AsyncSession = Depends(get_db)):
    """Cobros/pagos: cobrado vs pendiente, por medio de pago (fuente: comandas)."""
    return await lentes_svc.get_cobros(db, current_user["tenant_id"])


@router.get("/tesoreria", response_model=Tesoreria)
async def tesoreria(current_user: dict = MetricasReader, db: AsyncSession = Depends(get_db)):
    """Posición de tesorería: saldo por medio de pago (pedidos confirmados)."""
    return await lentes_svc.get_tesoreria(db, current_user["tenant_id"])


@router.get("/flujo-caja", response_model=list[FlujoPunto])
async def flujo_caja(
    meses: int = Query(12, ge=1, le=24),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Flujo de caja mensual: ingresos (ventas) − egresos (facturas de proveedor)."""
    return await lentes_svc.get_flujo_caja(db, current_user["tenant_id"], meses=meses)


@router.get("/actividad", response_model=list[ActividadItem])
async def actividad(
    limit: int = Query(30, ge=1, le=100),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Feed de actividad reciente: ventas + leads + conversaciones."""
    return await lentes_svc.get_actividad(db, current_user["tenant_id"], limit=limit)
