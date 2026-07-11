"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Tenant } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface TenantUpdateDto {
  nombre?: string;
  plan?: string;
  config?: Record<string, unknown>;
}

export function useTenant() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["tenant", tenantId],
    queryFn: () => api.get<Tenant>("/tenants/me"),
    enabled: Boolean(tenantId),
  });
}

export function useUpdateTenant() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: TenantUpdateDto) => api.patch<Tenant>("/tenants/me", dto),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
      notifications.show({
        color: "green",
        title: "Negocio actualizado",
        message: "Los cambios se guardaron correctamente.",
      });
    },
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "Error al guardar",
        message: error.message,
      });
    },
  });
}
