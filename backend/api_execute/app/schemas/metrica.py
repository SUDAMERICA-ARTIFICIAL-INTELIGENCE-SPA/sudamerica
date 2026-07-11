"""Metrica schemas for dashboard aggregation endpoints."""

from decimal import Decimal

from pydantic import BaseModel


class MetricaRevenue(BaseModel):
    total_revenue: Decimal
    total_ventas: int


class MetricaPorCanal(BaseModel):
    canal: str
    cantidad: int


class MetricaPorSector(BaseModel):
    sector: str
    cantidad: int


class MetricaProductoTop(BaseModel):
    producto_id: str
    nombre: str
    total_vendido: int
    revenue: Decimal


class MetricaConversion(BaseModel):
    total_leads: int
    convertidos: int
    tasa_conversion: float


class MetricaLeadEstado(BaseModel):
    estado: str
    cantidad: int


class DashboardKpis(BaseModel):
    ventas_mes: float
    meta_mes: float
    nuevos_leads: int
    tasa_conversion: float
    # AI metrics — computed from real conversation data
    ia_atendidas: int  # unique conversations (distinct lead_id) this month
    ia_mensajes: int  # total messages this month
    ia_auto_resueltas: int  # conversations resolved without human review
    ia_tasa_auto_resolucion: float  # auto-resolution rate (0-100)
    ia_total_tokens: int  # total LLM tokens consumed
    ia_costo_tokens_usd: float  # real token cost in USD
    ia_costo_por_conversacion: float  # avg token cost per conversation
    ia_horas_ahorradas: float  # estimated hours saved (5min × auto-resuelta)
    ahorro_ia_usd: float  # estimated savings in USD
    ia_roi: float  # ROI: ((ahorro - costo) / costo) × 100


class MetricaOperativa(BaseModel):
    revenue_total: float
    pedidos_entregados: int
    items_vendidos: int
    ticket_promedio: float
    comandas_canceladas: int
    comandas_abiertas: int


class RevenueDataPoint(BaseModel):
    fecha: str
    revenue_real: float
    revenue_forecast: float | None = None


class WeeklyActivityPoint(BaseModel):
    day: str
    ia: float
    humano: float


class FinancialSummary(BaseModel):
    total_ventas: int
    revenue: float
    cogs: float
    margen_bruto: float
    food_cost_pct: float
    margen_pct: float
    ticket_promedio: float
    items_vendidos: int
    productos_sin_costo: int
    period: str


class CustomerSegment(BaseModel):
    segmento: str
    cantidad: int
    total_gastado: float
    avg_frecuencia_dias: float


class AtRiskCustomer(BaseModel):
    id: str
    nombre: str | None = None
    estado_cliente: str | None = None
    total_gastado: float
    plato_favorito: str | None = None
    dias_sin_visita: int
    frecuencia_esperada: int


class LoyaltyInsights(BaseModel):
    total_vip_frecuente: int
    at_risk_customers: list[AtRiskCustomer]
    at_risk_count: int
    reactivation_candidates: int


class MenuEngineeringItem(BaseModel):
    """Menu Engineering matrix classification per BCG-style analysis."""

    producto_id: str
    nombre: str
    categoria: str | None = None
    unidades_vendidas: int
    revenue: float
    margen_pct: float
    clasificacion: str  # STAR, PUZZLE, PLOWHORSE, DOG
