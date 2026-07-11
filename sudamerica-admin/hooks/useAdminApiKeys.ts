"use client";

import { api } from "@/lib/api";
import type { PaginatedResponse, PlatformKeysResponse, TenantKeyItem } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";

export function usePlatformKeys() {
  return useQuery({
    queryKey: ["admin", "api-keys", "platform"],
    queryFn: () => api.get<PlatformKeysResponse>("/api-keys/platform"),
  });
}

interface TenantKeyFilters {
  page?: number;
  page_size?: number;
}

export function useTenantKeys(filters: TenantKeyFilters = {}) {
  const { page = 1, page_size = 20 } = filters;
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(page_size));

  return useQuery({
    queryKey: ["admin", "api-keys", "tenants", { page, page_size }],
    queryFn: () =>
      api.get<PaginatedResponse<TenantKeyItem>>(`/api-keys/tenants?${params.toString()}`),
  });
}

export function useRotateKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { provider: string; new_key: string; reason?: string }) =>
      api.post<{ success: boolean }>("/api-keys/platform/rotate", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "api-keys"] });
      notifications.show({ color: "green", title: "Key rotada", message: "La key fue actualizada exitosamente." });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
