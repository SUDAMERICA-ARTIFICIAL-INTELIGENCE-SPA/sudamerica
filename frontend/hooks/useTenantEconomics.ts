"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PaginatedResponse, TenantEconomicsSnapshot } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export interface TenantEconomicsFilters {
  page?: number;
  page_size?: number;
  desde?: string; // YYYY-MM
  hasta?: string; // YYYY-MM
}

export function useTenantEconomics(filters?: TenantEconomicsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["tenant-economics", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.desde) params.set("desde", filters.desde);
      if (filters?.hasta) params.set("hasta", filters.hasta);
      const qs = params.toString();
      return api.get<PaginatedResponse<TenantEconomicsSnapshot>>(
        `/tenant-economics${qs ? `?${qs}` : ""}`,
      );
    },
    enabled: !!tenantId,
  });
}

export function useLatestTenantEconomics() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["tenant-economics", "latest", { tenantId }],
    queryFn: () => api.get<TenantEconomicsSnapshot>("/tenant-economics/latest"),
    enabled: !!tenantId,
  });
}
