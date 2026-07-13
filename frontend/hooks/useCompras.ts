"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ── Tipos del dominio Compras (OLA B) ──

export interface Proveedor {
  id: string;
  nombre: string;
  rut: string | null;
  contacto_nombre: string | null;
  email: string | null;
  telefono: string | null;
  direccion: string | null;
  categoria: string | null;
  condicion_pago: string | null;
  lead_time_dias: number | null;
  rating: number | null;
  activo: boolean;
  cxp: number;
  total_comprado: number;
  ordenes_count: number;
}

export interface OCItem {
  id: string;
  producto_id: string | null;
  descripcion: string;
  cantidad: number;
  cantidad_recibida: number;
  costo_unitario: number;
  subtotal: number;
}

export interface OrdenCompra {
  id: string;
  proveedor_id: string;
  proveedor_nombre: string | null;
  numero: string;
  estado: string;
  fecha_emision: string;
  fecha_esperada: string | null;
  moneda: string;
  neto: number;
  iva: number;
  total: number;
  items_count: number;
  items: OCItem[];
}

export interface Recepcion {
  id: string;
  orden_compra_id: string;
  oc_numero: string | null;
  proveedor_nombre: string | null;
  numero: string;
  fecha: string;
  estado: string;
  recibido_por: string | null;
  items_count: number;
  total_unidades: number;
}

export interface FacturaProveedor {
  id: string;
  proveedor_id: string;
  proveedor_nombre: string | null;
  orden_compra_id: string | null;
  numero: string;
  fecha_emision: string;
  fecha_vencimiento: string | null;
  estado: string;
  neto: number;
  iva: number;
  total: number;
  monto_pagado: number;
  saldo: number;
  metodo_pago: string | null;
}

export interface Requisicion {
  id: string;
  numero: string;
  solicitante: string | null;
  estado: string;
  prioridad: string;
  fecha: string;
  items: Array<{ descripcion: string; cantidad: number; producto_id?: string }>;
  notas: string | null;
}

export interface Cotizacion {
  id: string;
  proveedor_id: string;
  proveedor_nombre: string | null;
  numero: string;
  estado: string;
  fecha: string;
  validez_dias: number;
  total: number;
  items: Array<{ descripcion: string; cantidad: number; costo_unitario: number }>;
}

export interface EvaluacionProveedor {
  proveedor_id: string;
  nombre: string;
  categoria: string | null;
  rating: number | null;
  ordenes_totales: number;
  ordenes_recibidas: number;
  puntualidad_pct: number;
  cumplimiento_pct: number;
  total_comprado: number;
  lead_time_dias: number | null;
}

export interface ComprasResumen {
  proveedores_activos: number;
  total_comprado_12m: number;
  cxp_total: number;
  cxp_vencida: number;
  ordenes_abiertas: number;
  ordenes_mes: number;
  facturas_pendientes: number;
}

interface Paged {
  page?: number;
  page_size?: number;
}

function qs(params: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function useComprasResumen() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "resumen", { tenantId }],
    queryFn: () => api.get<ComprasResumen>("/compras/resumen"),
    enabled: !!tenantId,
  });
}

export function useProveedores(filters?: Paged & { search?: string }) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "proveedores", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Proveedor>>(`/compras/proveedores${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useOrdenesCompra(filters?: Paged & { estado?: string }) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "ordenes", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<OrdenCompra>>(`/compras/ordenes${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useOrdenCompra(id: string | null) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "orden", { tenantId, id }],
    queryFn: () => api.get<OrdenCompra>(`/compras/ordenes/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useRecepciones(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "recepciones", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Recepcion>>(`/compras/recepciones${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useFacturasProveedor(filters?: Paged & { estado?: string }) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "facturas", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<FacturaProveedor>>(`/compras/facturas${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useRequisiciones(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "requisiciones", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Requisicion>>(`/compras/requisiciones${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useCotizaciones(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "cotizaciones", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Cotizacion>>(`/compras/cotizaciones${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useEvaluacionProveedores() {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["compras", "evaluacion", { tenantId }],
    queryFn: () => api.get<EvaluacionProveedor[]>("/compras/evaluacion"),
    enabled: !!tenantId,
  });
}

export function useCreateProveedor() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();
  return useMutation({
    mutationFn: (dto: Partial<Proveedor>) => api.post<Proveedor>("/compras/proveedores", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["compras", "proveedores", { tenantId }] });
      notifications.show({ color: "green", title: "Proveedor creado", message: "Se guardó el proveedor." });
    },
    onError: (err: Error) =>
      notifications.show({ color: "red", title: "Error", message: err.message }),
  });
}
