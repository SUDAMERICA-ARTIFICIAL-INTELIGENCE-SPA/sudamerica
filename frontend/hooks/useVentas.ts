"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiResponse, PaginatedResponse, Venta } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface VentasFilters {
  page?: number;
  page_size?: number;
  asesor_id?: string;
  lead_id?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}

/** NOTE: Venta.total is IMMUTABLE (server-computed). No update mutation. */
export interface CreateVentaDto {
  lead_id: string;
  producto_id: string;
  ai_assisted: boolean;
}

export function useVentas(filters?: VentasFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["ventas", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.asesor_id) params.set("asesor_id", filters.asesor_id);
      if (filters?.lead_id) params.set("lead_id", filters.lead_id);
      if (filters?.fecha_desde) params.set("fecha_desde", filters.fecha_desde);
      if (filters?.fecha_hasta) params.set("fecha_hasta", filters.fecha_hasta);
      const qs = params.toString();
      return api.get<PaginatedResponse<Venta>>(`/ventas${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useVenta(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["ventas", id, { tenantId }],
    queryFn: () => api.get<Venta>(`/ventas/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useCreateVenta() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateVentaDto) => api.post<Venta>("/ventas", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ventas", { tenantId }] });
      void qc.invalidateQueries({ queryKey: ["metricas"] });
      notifications.show({
        color: "green",
        title: "Venta registrada",
        message: "¡Excelente cierre!",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al registrar venta", message: err.message });
    },
  });
}

export function useDeleteVenta() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) => api.patch<ApiResponse<Venta>>(`/ventas/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ventas", { tenantId }] });
      void qc.invalidateQueries({ queryKey: ["metricas"] });
      notifications.show({
        color: "orange",
        title: "Venta anulada",
        message: "La venta fue anulada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al anular", message: err.message });
    },
  });
}
