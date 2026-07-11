import { DEMO_DATES, DEMO_TIMESTAMPS, SECTOR_PROFILE, makeRng, roundTo } from "@/lib/demo/gen";
import { DEMO_TENANT_ID } from "@/lib/demo/state";
// ── Fixtures demo type-correct por rubro ───────────────────────────────────
// Cada builder crea su propio RNG sembrado por (key + salt de endpoint) → los
// resultados son deterministas e independientes del orden de llamada. Todos los
// objetos calzan 1:1 con las interfaces de `lib/types.ts`.
import { LeadCanal, type RevisionAccion, SmartAlertType, TenantPlan, UserRole } from "@/lib/enums";
import { RUBROS, type RubroKey, rubroSectorConfig } from "@/lib/rubros";
import type {
  AIConversation,
  DashboardKpis,
  FinancialSummary,
  MenuEngineeringItem,
  OperationalSummary,
  PaginatedResponse,
  RevenueDataPoint,
  RevisionHumana,
  SmartAlert,
  Tenant,
  TopProduct,
  Usuario,
  WeeklyActivityPoint,
} from "@/lib/types";

const DESCRIPTORS = [
  "Premium",
  "Clásico",
  "Estándar",
  "Pro",
  "Especial",
  "Familiar",
  "Express",
] as const;
const CANALES = [
  LeadCanal.WHATSAPP,
  LeadCanal.INSTAGRAM,
  LeadCanal.WEB,
  LeadCanal.FACEBOOK,
] as const;
const ALERT_TYPES = [
  SmartAlertType.HOT_LEAD,
  SmartAlertType.STALLED_DEAL,
  SmartAlertType.CHURN_RISK,
  SmartAlertType.ANOMALY_DETECTED,
  SmartAlertType.NO_SHOW_RISK,
] as const;

function ts(i: number): string {
  return DEMO_TIMESTAMPS[i % DEMO_TIMESTAMPS.length] as string;
}

function ticketStep(maxTicket: number): number {
  if (maxTicket >= 1_000_000) return 10_000;
  if (maxTicket >= 100_000) return 1000;
  return 100;
}

/** Métricas económicas base de un rubro (compartidas entre endpoints coherentes). */
function economics(key: RubroKey) {
  const rng = makeRng(key, "econ");
  const p = SECTOR_PROFILE[RUBROS[key].sector];
  const ticket = roundTo(rng.int(p.ticket[0], p.ticket[1]), ticketStep(p.ticket[1]));
  const volume = rng.int(p.volume[0], p.volume[1]);
  const ventasMes = roundTo(ticket * volume, 1000);
  const attain = rng.float(0.78, 1.14);
  const metaMes = roundTo(ventasMes / attain, 1000);
  const leads = rng.int(p.leads[0], p.leads[1]);
  const conversion = Math.round(rng.float(12, 40) * 10) / 10;
  const cogsPct = rng.float(p.cogsPct[0], p.cogsPct[1]);
  return { ticket, volume, ventasMes, metaMes, leads, conversion, cogsPct };
}

export function buildTenant(key: RubroKey): Tenant {
  const def = RUBROS[key];
  return {
    id: DEMO_TENANT_ID,
    nombre: `${def.nombre} Demo`,
    slug: key,
    plan: TenantPlan.PRO,
    max_users: 15,
    max_leads_mes: 100000,
    stripe_customer_id: null,
    stripe_subscription_id: null,
    config: { rubro: key },
    sector: def.sector,
    activo: true,
    created_at: "2026-01-15T10:00:00Z",
    updated_at: DEMO_TIMESTAMPS[0] as string,
  };
}

export function buildUser(): Usuario {
  return {
    id: "demo-user",
    tenant_id: DEMO_TENANT_ID,
    nombre: "Demo",
    apellido: "Showroom",
    email: "demo@sudamerica.ai",
    role: UserRole.ADMIN,
    sucursal_id: null,
    email_verified: true,
    activo: true,
    created_at: "2026-01-15T10:00:00Z",
    updated_at: DEMO_TIMESTAMPS[0] as string,
  };
}

export function buildDashboardKpis(key: RubroKey): DashboardKpis {
  const rng = makeRng(key, "kpis");
  const e = economics(key);
  const iaAtendidas = Math.round(e.leads * rng.float(0.45, 0.85));
  const iaMensajes = iaAtendidas * rng.int(4, 11);
  const iaAutoResueltas = Math.round(iaAtendidas * rng.float(0.6, 0.9));
  const iaTotalTokens = iaMensajes * rng.int(280, 620);
  const iaCostoTokensUsd =
    Math.round((iaTotalTokens / 1_000_000) * rng.float(0.4, 0.9) * 100) / 100;
  const iaHorasAhorradas = Math.round(iaAutoResueltas * 0.75 * 10) / 10;
  return {
    ventas_mes: e.ventasMes,
    meta_mes: e.metaMes,
    nuevos_leads: e.leads,
    tasa_conversion: e.conversion,
    ia_atendidas: iaAtendidas,
    ia_mensajes: iaMensajes,
    ia_auto_resueltas: iaAutoResueltas,
    ia_tasa_auto_resolucion:
      iaAtendidas > 0 ? Math.round((iaAutoResueltas / iaAtendidas) * 1000) / 10 : 0,
    ia_total_tokens: iaTotalTokens,
    ia_costo_tokens_usd: iaCostoTokensUsd,
    ia_costo_por_conversacion:
      iaAtendidas > 0 ? Math.round((iaCostoTokensUsd / iaAtendidas) * 10000) / 10000 : 0,
    ia_horas_ahorradas: iaHorasAhorradas,
    ahorro_ia_usd: roundTo(iaHorasAhorradas * rng.int(6, 18), 10),
    ia_roi: Math.round(rng.float(120, 640)),
    avg_lead_response_time_ms: rng.int(40_000, 900_000),
  };
}

export function buildRevenue(key: RubroKey): RevenueDataPoint[] {
  const rng = makeRng(key, "revenue");
  const e = economics(key);
  const base = e.ventasMes / DEMO_DATES.length;
  const weekendUp = ["gastronomia", "retail", "turismo"].includes(RUBROS[key].sector);
  return DEMO_DATES.map((fecha, i) => {
    const weekday = i % 7;
    const weekendFactor = weekday >= 5 ? (weekendUp ? 1.25 : 0.7) : 1;
    const trend = 1 + i * 0.006; // leve alza en el período
    const noise = rng.float(0.85, 1.15);
    const real = roundTo(base * weekendFactor * trend * noise, 1000);
    const forecast = roundTo(real * rng.float(0.94, 1.09), 1000);
    return { fecha, revenue_real: real, revenue_forecast: forecast };
  });
}

export function buildOperational(key: RubroKey): OperationalSummary {
  const rng = makeRng(key, "operativo");
  const e = economics(key);
  return {
    revenue_total: roundTo(e.ventasMes * rng.float(0.9, 1.05), 1000),
    pedidos_entregados: e.volume,
    items_vendidos: Math.round(e.volume * rng.float(1.2, 3.0)),
    ticket_promedio: e.ticket,
    comandas_canceladas: Math.round(e.volume * rng.float(0.01, 0.05)),
    comandas_abiertas: rng.int(0, 12),
  };
}

export function buildTopProducts(key: RubroKey, limit: number): TopProduct[] {
  const rng = makeRng(key, "productos");
  const e = economics(key);
  const cats = RUBROS[key].categoriasSemilla;
  const n = Math.min(limit, cats.length);
  const items = Array.from({ length: n }, (_, i) => {
    const nombre = `${cats[i]} ${rng.pick(DESCRIPTORS)}`;
    const total = rng.int(20, 320);
    return {
      producto_id: `demo-prod-${key}-${i}`,
      nombre,
      total_vendido: total,
      revenue: roundTo(total * e.ticket * rng.float(0.6, 1.2), 1000),
    };
  });
  return items.sort((a, b) => b.revenue - a.revenue);
}

export function buildFinancial(key: RubroKey): FinancialSummary {
  const rng = makeRng(key, "financiero");
  const e = economics(key);
  const revenue = e.ventasMes;
  const cogs = roundTo(revenue * e.cogsPct, 1000);
  const margenBruto = revenue - cogs;
  return {
    total_ventas: e.volume,
    revenue,
    cogs,
    margen_bruto: margenBruto,
    food_cost_pct: Math.round(e.cogsPct * 1000) / 10,
    margen_pct: revenue > 0 ? Math.round((margenBruto / revenue) * 1000) / 10 : 0,
    ticket_promedio: e.ticket,
    items_vendidos: Math.round(e.volume * rng.float(1.2, 3.0)),
    productos_sin_costo: rng.int(0, 4),
    period: "2026-07",
  };
}

const MENU_CLASES = ["STAR", "PUZZLE", "PLOWHORSE", "DOG"] as const;

export function buildMenuEngineering(key: RubroKey): MenuEngineeringItem[] {
  const rng = makeRng(key, "menu-eng");
  const e = economics(key);
  const cats = RUBROS[key].categoriasSemilla;
  return cats.slice(0, 6).map((cat, i) => {
    const unidades = rng.int(15, 260);
    return {
      producto_id: `demo-menu-${key}-${i}`,
      nombre: `${cat} ${rng.pick(DESCRIPTORS)}`,
      categoria: cat,
      unidades_vendidas: unidades,
      revenue: roundTo(unidades * e.ticket * rng.float(0.6, 1.2), 1000),
      margen_pct: Math.round(rng.float(18, 74) * 10) / 10,
      clasificacion: MENU_CLASES[i % MENU_CLASES.length] as MenuEngineeringItem["clasificacion"],
    };
  });
}

const DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] as const;

export function buildWeeklyActivity(key: RubroKey): WeeklyActivityPoint[] {
  const rng = makeRng(key, "weekly");
  return DAYS.map((day) => ({
    day,
    ia: rng.int(8, 90),
    humano: rng.int(2, 40),
  }));
}

export function buildConversations(
  key: RubroKey,
  pageSize: number,
): PaginatedResponse<AIConversation> {
  const rng = makeRng(key, "conversations");
  const e = economics(key);
  const total = Math.round(e.leads * rng.float(0.45, 0.85));
  const n = Math.min(pageSize, Math.max(total, 1));
  const data: AIConversation[] = Array.from({ length: n }, (_, i) => ({
    id: `demo-conv-${key}-${i}`,
    tenant_id: DEMO_TENANT_ID,
    lead_id: `demo-lead-${key}-${i}`,
    canal: rng.pick(CANALES),
    resuelto_sin_humano: rng.bool(0.72),
    confidence: Math.round(rng.float(0.7, 0.99) * 100) / 100,
    token_cost: Math.round(rng.float(0.001, 0.02) * 10000) / 10000,
    duracion_segundos: rng.int(20, 480),
    created_at: ts(i),
  }));
  return {
    data,
    meta: {
      total,
      page: 1,
      page_size: pageSize,
      total_pages: Math.max(1, Math.ceil(total / pageSize)),
    },
  };
}

export function buildRevisiones(
  key: RubroKey,
  pageSize: number,
): PaginatedResponse<RevisionHumana> {
  const rng = makeRng(key, "pendientes");
  const total = rng.int(0, 6);
  const n = Math.min(pageSize, total);
  const data: RevisionHumana[] = Array.from({ length: n }, (_, i) => ({
    id: `demo-rev-${key}-${i}`,
    tenant_id: DEMO_TENANT_ID,
    conversation_id: `demo-conv-${key}-${i}`,
    asesor_id: null,
    accion: null as RevisionAccion | null,
    pendiente: true,
    created_at: ts(i),
    reviewed_at: null,
  }));
  return {
    data,
    meta: {
      total,
      page: 1,
      page_size: pageSize,
      total_pages: Math.max(1, Math.ceil(total / pageSize)),
    },
  };
}

export function buildAlerts(key: RubroKey, pageSize: number): PaginatedResponse<SmartAlert> {
  const rng = makeRng(key, "alertas");
  const def = RUBROS[key];
  const L = def.labels;
  const mensajePorTipo: Record<SmartAlertType, string> = {
    [SmartAlertType.HOT_LEAD]: `${L.parte} con alta intención pidió ${L.item.toLowerCase()} premium`,
    [SmartAlertType.STALLED_DEAL]: `${L.orden} sin avance hace 6 días`,
    [SmartAlertType.CHURN_RISK]: `${L.parte} frecuente sin volver hace 40 días`,
    [SmartAlertType.ANOMALY_DETECTED]: "Caída de actividad 32% vs. semana anterior",
    [SmartAlertType.NO_SHOW_RISK]: `${L.agenda} con riesgo de inasistencia mañana`,
  };
  const total = rng.int(3, 8);
  const n = Math.min(pageSize, total);
  const data: SmartAlert[] = Array.from({ length: n }, (_, i) => {
    const tipo = ALERT_TYPES[i % ALERT_TYPES.length] as SmartAlertType;
    return {
      id: `demo-alert-${key}-${i}`,
      tenant_id: DEMO_TENANT_ID,
      tipo,
      lead_id: `demo-lead-${key}-${i}`,
      mensaje: mensajePorTipo[tipo],
      leido: false,
      created_at: ts(i),
    };
  });
  return {
    data,
    meta: {
      total,
      page: 1,
      page_size: pageSize,
      total_pages: Math.max(1, Math.ceil(total / pageSize)),
    },
  };
}

/** Info de sector (contexto data-free) — usado por SectorInsight vía useRubroLabels. */
export function sectorLabel(key: RubroKey): string {
  return rubroSectorConfig(key).label;
}
