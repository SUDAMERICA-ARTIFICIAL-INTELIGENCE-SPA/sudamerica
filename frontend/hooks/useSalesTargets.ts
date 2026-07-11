"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiResponse, PaginatedResponse, SalesTarget } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface SalesTargetsFilters {
  page?: number;
  page_size?: number;
  asesor_id?: string;
  periodo?: string; // YYYY-MM
}

export interface UpsertSalesTargetDto {
  asesor_id?: string;
  periodo: string;
  meta_ventas: number;
  meta_leads: number;
  meta_conversion: number;
}

export function useSalesTargets(filters?: SalesTargetsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["sales-targets", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.asesor_id) params.set("asesor_id", filters.asesor_id);
      if (filters?.periodo) params.set("periodo", filters.periodo);
      const qs = params.toString();
      return api.get<PaginatedResponse<SalesTarget>>(`/sales-targets${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useUpsertSalesTarget() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: UpsertSalesTargetDto) =>
      api.post<ApiResponse<SalesTarget>>("/sales-targets", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sales-targets", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Meta guardada",
        message: "Los objetivos del período fueron actualizados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al guardar meta", message: err.message });
    },
  });
}
