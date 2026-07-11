import type {
  CalendarEventTipo,
  CanalOrigen,
  ClienteEstado,
  ComandaEstado,
  LeadCanal,
  LeadEstado,
  ModifierGroupTipo,
  QuoteEstado,
  RevisionAccion,
  SmartAlertType,
  SubAgenteType,
  TenantPlan,
  TipoEntrega,
  UserRole,
} from "@/lib/enums";

// ─── Core Entities ────────────────────────────────────────────────────────────

export interface Tenant {
  id: string;
  nombre: string;
  slug: string;
  plan: TenantPlan;
  max_users: number;
  max_leads_mes: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  config: Record<string, unknown> | null;
  sector?: string;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Usuario {
  id: string;
  tenant_id: string;
  nombre: string;
  apellido: string;
  email: string;
  role: UserRole;
  sucursal_id: string | null;
  email_verified: boolean;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  tenant_id: string;
  sucursal_id: string | null;
  nombre: string;
  email: string | null;
  telefono: string | null;
  canal: LeadCanal;
  estado: LeadEstado;
  valor_estimado: number | null;
  ai_score: number | null;
  asesor_id: string | null;
  sector_data: Record<string, unknown> | null;
  estado_cliente: ClienteEstado | null;
  total_pedidos: number;
  total_gastado: number;
  plato_favorito: string | null;
  ultima_visita: string | null;
  frecuencia_dias: number | null;
  tags: string[] | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

/** Sub-entidad del cliente (mascota/vehículo/paciente…), módulo sub_entidad F6. */
export interface ClienteSubentidad {
  id: string;
  tenant_id: string;
  lead_id: string;
  tipo: string;
  nombre: string;
  datos: Record<string, unknown>;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Producto {
  id: string;
  tenant_id: string;
  nombre: string;
  descripcion: string | null;
  precio: number;
  costo: number | null;
  stock: number;
  /** Umbral de alerta stock_bajo (módulo inventario, F3); opcional para APIs previas a la migración 022. */
  stock_minimo?: number;
  /** Unidad del precio (unidad/kg/m2/hora…), módulo precio_medida F6; opcional pre-migración 026. */
  unidad_venta?: string;
  categoria_id: string | null;
  imagen_url: string | null;
  disponible: boolean;
  activo: boolean;
  created_at: string;
}

export interface Categoria {
  id: string;
  tenant_id: string;
  nombre: string;
  activo: boolean;
}

// ── Menu Import (preview/confirm workflow) ──

export interface MenuImportPreviewItem {
  nombre: string;
  descripcion: string | null;
  precio: number;
  categoria: string;
}

export interface MenuImportPreview {
  import_id: string;
  items: MenuImportPreviewItem[];
  source_type: string;
  filename: string | null;
}

export interface MenuImportConfirmResult {
  created: number;
  categories_created: number;
  errors: string[];
  import_id: string;
  version: number;
}

export interface MenuImportHistoryItem {
  id: string;
  version: number;
  source_type: string;
  filename: string | null;
  items_extracted: number;
  items_confirmed: number;
  categories_created: number;
  status: string;
  set_as_official: boolean;
  original_pdf_url: string | null;
  created_at: string;
}

export interface Venta {
  id: string;
  tenant_id: string;
  sucursal_id: string | null;
  lead_id: string;
  asesor_id: string;
  producto_id: string;
  total: number; // IMMUTABLE â€” server-computed
  ai_assisted: boolean;
  created_at: string;
}

export interface AgenteConfig {
  id: string;
  tenant_id: string;
  tipo: SubAgenteType;
  activo: boolean;
  config: Record<string, unknown>;
  updated_at: string;
}

export interface AIConversation {
  id: string;
  tenant_id: string;
  lead_id: string;
  canal: LeadCanal;
  resuelto_sin_humano: boolean;
  confidence: number;
  token_cost: number;
  duracion_segundos: number;
  created_at: string;
}

export interface RevisionHumana {
  id: string;
  tenant_id: string;
  conversation_id: string;
  asesor_id: string | null;
  accion: RevisionAccion | null;
  pendiente: boolean;
  created_at: string;
  reviewed_at: string | null;
}

// ─── New Tables (backend in development) ─────────────────────────────────────

export interface LeadStageHistory {
  id: string;
  lead_id: string;
  estado_anterior: LeadEstado | null;
  estado_nuevo: LeadEstado;
  asesor_id: string | null;
  created_at: string;
}

export interface LeadInteraction {
  id: string;
  lead_id: string;
  tenant_id: string;
  tipo: string;
  descripcion: string;
  asesor_id: string | null;
  created_at: string;
}

export interface SalesTarget {
  id: string;
  tenant_id: string;
  asesor_id: string | null;
  periodo: string; // YYYY-MM
  meta_ventas: number;
  meta_leads: number;
  meta_conversion: number;
}

export interface SmartAlert {
  id: string;
  tenant_id: string;
  tipo: SmartAlertType;
  lead_id: string | null;
  mensaje: string;
  leido: boolean;
  created_at: string;
}

export interface TenantEconomicsSnapshot {
  id: string;
  tenant_id: string;
  periodo: string; // YYYY-MM
  revenue: number;
  leads_total: number;
  leads_convertidos: number;
  costo_ai: number;
  horas_ahorradas: number;
  created_at: string;
}

export interface CalendarEvent {
  id: string;
  tenant_id: string;
  lead_id: string | null;
  asesor_id: string;
  titulo: string;
  descripcion: string | null;
  fecha_inicio: string;
  fecha_fin: string | null;
  tipo: CalendarEventTipo;
  activo: boolean;
  created_at: string;
}

export interface QuoteLineItem {
  producto_id: string;
  cantidad: number;
  precio_unitario: number;
}

export interface QuoteEstimate {
  id: string;
  tenant_id: string;
  lead_id: string;
  asesor_id: string;
  productos: QuoteLineItem[];
  total: number;
  estado: QuoteEstado;
  notas: string | null;
  created_at: string;
  updated_at: string;
}

export interface Mesa {
  id: string;
  tenant_id: string;
  sucursal_id: string | null;
  numero: number;
  nombre: string | null;
  capacidad: number;
  qr_token: string;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Sucursal {
  id: string;
  tenant_id: string;
  nombre: string;
  slug: string;
  direccion: string | null;
  telefono: string | null;
  horario: Record<string, unknown> | null;
  zona_delivery: string | null;
  latitud: number | null;
  longitud: number | null;
  config: Record<string, unknown> | null;
  es_principal: boolean;
  ciudad: string | null;
  region: string | null;
  codigo_postal: string | null;
  pais: string;
  google_maps_url: string | null;
  costo_delivery: number;
  grupo_repartidores_jid: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Sudamérica AI Resto (Gastronomy) ────────────────────────────────────────────────

export interface ModifierGroup {
  id: string;
  tenant_id: string;
  nombre: string;
  tipo: ModifierGroupTipo;
  obligatorio: boolean;
  max_selecciones: number | null;
  modifiers: Modifier[];
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Modifier {
  id: string;
  tenant_id: string;
  grupo_id: string;
  nombre: string;
  precio_delta: number;
  orden: number;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComandaItem {
  id: string;
  comanda_id: string;
  producto_id: string;
  cantidad: number;
  precio_unitario: number;
  modifiers_json: Array<{
    modifier_id: string;
    nombre: string;
    precio_delta: number;
  }>;
  subtotal: number;
  notas: string | null;
  producto_nombre: string | null;
}

export interface Comanda {
  id: string;
  tenant_id: string;
  sucursal_id: string | null;
  venta_id: string | null;
  cliente_id: string | null;
  tipo_entrega: TipoEntrega;
  numero_mesa: number | null;
  estado: ComandaEstado;
  canal_origen: CanalOrigen;
  notas: string | null;
  prioridad: number;
  tiempo_estimado_min: number | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
  entregado_at: string | null;
  direccion_entrega: string | null;
  ubicacion_lat: number | null;
  ubicacion_lng: number | null;
  metodo_pago: string | null;
  costo_delivery: number;
  pago_confirmado: boolean;
  repartidor_nombre: string | null;
  repartidor_phone: string | null;
  items: ComandaItem[];
  cliente_nombre: string | null;
}

export interface KDSView {
  PENDIENTE: Comanda[];
  EN_COCINA: Comanda[];
  LISTO: Comanda[];
}

// ─── API Response Envelopes ───────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

// ─── JWT & Auth ───────────────────────────────────────────────────────────────

export interface JwtPayload {
  sub: string; // user_id
  tenant_id: string;
  role: UserRole;
  sucursal_id?: string;
  exp: number;
  iat: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface AuthState {
  user: Usuario | null;
  tokens: AuthTokens | null;
  tenantId: string | null;
  sucursalId: string | null;
}

// ─── Dashboard & Metrics ──────────────────────────────────────────────────────

export interface DashboardKpis {
  ventas_mes: number;
  meta_mes: number;
  nuevos_leads: number;
  tasa_conversion: number;
  // AI metrics — all computed from real conversation data
  ia_atendidas: number; // unique conversations (distinct lead_id)
  ia_mensajes: number; // total messages
  ia_auto_resueltas: number; // conversations without human review
  ia_tasa_auto_resolucion: number; // auto-resolution rate (0-100)
  ia_total_tokens: number; // LLM tokens consumed
  ia_costo_tokens_usd: number; // real token cost in USD
  ia_costo_por_conversacion: number; // avg cost per conversation
  ia_horas_ahorradas: number; // estimated hours saved
  ahorro_ia_usd: number; // estimated savings in USD
  ia_roi: number; // ROI percentage
  avg_lead_response_time_ms?: number;
}

export interface WeeklyActivityPoint {
  day: string;
  ia: number;
  humano: number;
}

export interface OperationalSummary {
  revenue_total: number;
  pedidos_entregados: number;
  items_vendidos: number;
  ticket_promedio: number;
  comandas_canceladas: number;
  comandas_abiertas: number;
}

export interface TopProduct {
  producto_id: string;
  nombre: string;
  total_vendido: number;
  revenue: number;
}

export interface FinancialSummary {
  total_ventas: number;
  revenue: number;
  cogs: number;
  margen_bruto: number;
  food_cost_pct: number;
  margen_pct: number;
  ticket_promedio: number;
  items_vendidos: number;
  productos_sin_costo: number;
  period: string;
}

export interface MenuEngineeringItem {
  producto_id: string;
  nombre: string;
  categoria: string | null;
  unidades_vendidas: number;
  revenue: number;
  margen_pct: number;
  clasificacion: "STAR" | "PUZZLE" | "PLOWHORSE" | "DOG";
}

export interface RevenueDataPoint {
  fecha: string;
  revenue_real: number;
  revenue_forecast?: number | null;
}
