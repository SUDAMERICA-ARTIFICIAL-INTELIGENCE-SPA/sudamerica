"use client";

import { api } from "@/lib/api";
import type { PaginatedResponse, WhatsAppInstance } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";

interface WhatsAppFilters {
  page?: number;
  page_size?: number;
}

export function useWhatsAppInstances(filters: WhatsAppFilters = {}) {
  const { page = 1, page_size = 20 } = filters;
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(page_size));

  return useQuery({
    queryKey: ["admin", "whatsapp", "instances", { page, page_size }],
    queryFn: () =>
      api.get<PaginatedResponse<WhatsAppInstance>>(
        `/whatsapp/instances?${params.toString()}`,
      ),
    refetchInterval: 30_000,
  });
}

export function useReconnectInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tenantId: string) =>
      api.post<{ status: string }>(`/whatsapp/${tenantId}/reconnect`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "whatsapp"] });
      notifications.show({ color: "green", title: "Reconexión solicitada", message: "" });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
