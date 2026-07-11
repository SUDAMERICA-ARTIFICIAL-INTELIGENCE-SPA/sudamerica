"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { SmartAlertType } from "@/lib/enums";
import type { ApiResponse, PaginatedResponse, SmartAlert } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface SmartAlertsFilters {
  page?: number;
  page_size?: number;
  tipo?: SmartAlertType;
  leido?: boolean;
}

export function useSmartAlerts(filters?: SmartAlertsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["alertas", { tenantId, ...filters }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.tipo) params.set("tipo", filters.tipo);
      if (filters?.leido !== undefined) params.set("leido", String(filters.leido));
      const qs = params.toString();
      try {
        return await api.get<PaginatedResponse<SmartAlert>>(`/alertas${qs ? `?${qs}` : ""}`);
      } catch {
        // Endpoint not yet implemented — return empty response
        return {
          success: true,
          data: [],
          error: null,
          meta: { total: 0, page: 1, page_size: 20, total_pages: 1 },
        } as PaginatedResponse<SmartAlert>;
      }
    },
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000, // check every 5 minutes (endpoint not yet active)
  });
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.patch<ApiResponse<SmartAlert>>(`/alertas/${id}`, { leido: true }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["alertas", { tenantId }] });
    },
  });
}
