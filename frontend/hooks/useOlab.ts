"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ── Dominios chicos de OLA B (B3) ──

export interface Devolucion {
  id: string;
  lead_id: string | null;
  venta_id: string | null;
  cliente_nombre: string | null;
  numero: string;
  fecha: string;
  motivo: string;
  estado: string;
  metodo_reembolso: string | null;
  monto: number;
  items: Array<{ producto: string; cantidad: number; monto: number }>;
  notas: string | null;
}

export interface Plantilla {
  id: string;
  nombre: string;
  canal: string;
  categoria: string | null;
  contenido: string;
  variables: string[];
  usos: number;
  activo: boolean;
}

export interface Documento {
  id: string;
  nombre: string;
  tipo: string;
  categoria: string | null;
  url: string | null;
  mime: string | null;
  tamano_kb: number | null;
  subido_por: string | null;
  entidad_tipo: string | null;
  created_at: string | null;
}

export interface Campana {
  id: string;
  nombre: string;
  canal: string;
  tipo: string;
  estado: string;
  segmento: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  presupuesto: number;
  enviados: number;
  abiertos: number;
  conversiones: number;
  ingresos_generados: number;
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

export function useDevoluciones(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["devoluciones", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Devolucion>>(`/devoluciones${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function usePlantillas(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["plantillas", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Plantilla>>(`/plantillas${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useDocumentos(filters?: Paged & { tipo?: string }) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["documentos", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Documento>>(`/documentos${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useCampanas(filters?: Paged) {
  const { tenantId } = useAuth();
  return useQuery({
    queryKey: ["campanas", { tenantId, ...filters }],
    queryFn: () => api.get<PaginatedResponse<Campana>>(`/campanas${qs({ ...filters })}`),
    enabled: !!tenantId,
  });
}

export function useCreateCampana() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();
  return useMutation({
    mutationFn: (dto: Partial<Campana>) => api.post<Campana>("/campanas", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["campanas", { tenantId }] });
      notifications.show({ color: "green", title: "Campaña creada", message: "Se guardó la campaña." });
    },
    onError: (err: Error) => notifications.show({ color: "red", title: "Error", message: err.message }),
  });
}
