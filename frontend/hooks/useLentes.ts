"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PaginatedResponse } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

// ── Lentes derivadas de OLA A (B1) ──

export interface CobroPorMetodo {
  metodo: string;
  cobrado: number;
  pendiente: number;
  pedidos: number;
}
export interface CobroPendiente {
  comanda_id: string;
  cliente: string | null;
  monto: number;
  metodo: string | null;
  estado: string;
  fecha: string;
}
export interface CobrosResumen {
  total_cobrado: number;
  total_pendiente: number;
  pedidos_cobrados: number;
  pedidos_pendientes: number;
  por_metodo: CobroPorMetodo[];
  pendientes_recientes: CobroPendiente[];
}
export interface SaldoMetodo {
  metodo: string;
  saldo: number;
  movimientos: number;
}
export interface Tesoreria {
  saldo_total: number;
  por_metodo: SaldoMetodo[];
}
export interface FlujoPunto {
  periodo: string;
  ingresos: number;
  egresos: number;
  neto: number;
}
export interface ActividadItem {
  tipo: string;
  titulo: string;
  subtitulo: string | null;
  monto: number | null;
  fecha: string;
}
export interface MovimientoKardex {
  fecha: string;
  tipo: string;
  producto: string | null;
  producto_id: string | null;
  cantidad: number;
  costo_unitario: number | null;
  referencia: string | null;
}

export function useCobros() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "cobros", { tenantId }],
    queryFn: () => api.get<CobrosResumen>("/metricas/cobros"),
    enabled: !!tenantId,
  });
}

export function useTesoreria() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "tesoreria", { tenantId }],
    queryFn: () => api.get<Tesoreria>("/metricas/tesoreria"),
    enabled: !!tenantId,
  });
}

export function useFlujoCaja(meses = 12) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "flujo-caja", { tenantId, meses }],
    queryFn: () => api.get<FlujoPunto[]>(`/metricas/flujo-caja?meses=${meses}`),
    enabled: !!tenantId,
  });
}

export function useActividad(limit = 30) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "actividad", { tenantId, limit }],
    queryFn: () => api.get<ActividadItem[]>(`/metricas/actividad?limit=${limit}`),
    enabled: !!tenantId,
  });
}

export interface CustomerSegment {
  segmento: string;
  cantidad: number;
  total_gastado: number;
  avg_frecuencia_dias: number;
}
export interface AtRiskCustomer {
  id: string;
  nombre: string;
  estado_cliente: string;
  total_gastado: number;
  plato_favorito: string | null;
  dias_sin_visita: number;
  frecuencia_esperada: number;
}
export interface LoyaltyInsights {
  total_vip_frecuente: number;
  at_risk_customers: AtRiskCustomer[];
  [k: string]: unknown;
}
export interface CanalCount {
  canal: string;
  cantidad: number;
}

export function useSegmentacion() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "segmentacion", { tenantId }],
    queryFn: () => api.get<CustomerSegment[]>("/metricas/segmentacion-clientes"),
    enabled: !!tenantId,
  });
}

export function useLoyaltyInsights() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "loyalty-insights", { tenantId }],
    queryFn: () => api.get<LoyaltyInsights>("/metricas/loyalty-insights"),
    enabled: !!tenantId,
  });
}

export function usePorCanal() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["metricas", "por-canal", { tenantId }],
    queryFn: () => api.get<CanalCount[]>("/metricas/por-canal"),
    enabled: !!tenantId,
  });
}

export function useMovimientos(filters?: { page?: number; page_size?: number; tipo?: string }) {
  const { tenantId } = useAuth();
  const p = new URLSearchParams();
  if (filters?.page) p.set("page", String(filters.page));
  if (filters?.page_size) p.set("page_size", String(filters.page_size));
  if (filters?.tipo) p.set("tipo", filters.tipo);
  const s = p.toString();
  return useQuery({
    queryKey: ["inventario", "movimientos", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<MovimientoKardex>>(`/inventario/movimientos${s ? `?${s}` : ""}`),
    enabled: !!tenantId,
  });
}
