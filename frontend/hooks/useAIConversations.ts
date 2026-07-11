"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AIConversation, PaginatedResponse } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export interface AIConversationsFilters {
  page?: number;
  page_size?: number;
  lead_id?: string;
  resuelto_sin_humano?: boolean;
  fecha_desde?: string;
  fecha_hasta?: string;
}

export function useAIConversations(filters?: AIConversationsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["ai-conversations", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.lead_id) params.set("lead_id", filters.lead_id);
      if (filters?.resuelto_sin_humano !== undefined)
        params.set("resuelto_sin_humano", String(filters.resuelto_sin_humano));
      if (filters?.fecha_desde) params.set("fecha_desde", filters.fecha_desde);
      if (filters?.fecha_hasta) params.set("fecha_hasta", filters.fecha_hasta);
      const qs = params.toString();
      return api.get<PaginatedResponse<AIConversation>>(`/ai-conversations${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useAIConversation(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["ai-conversations", id, { tenantId }],
    queryFn: () => api.get<AIConversation>(`/ai-conversations/${id}`),
    enabled: !!tenantId && !!id,
  });
}
