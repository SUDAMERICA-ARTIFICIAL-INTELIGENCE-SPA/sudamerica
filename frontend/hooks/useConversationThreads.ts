"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";

export interface ConversationThread {
  lead_id: string;
  lead_name: string | null;
  session_id: string | null;
  last_message: string;
  last_role: string;
  last_canal: string | null;
  message_count: number;
  last_message_at: string;
}

interface PaginatedThreads {
  data: ConversationThread[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export interface ThreadFilters {
  page?: number;
  page_size?: number;
  canal?: string | undefined;
}

export function useConversationThreads(filters?: ThreadFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["conversation-threads", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.canal) params.set("canal", filters.canal);
      const qs = params.toString();
      return api.get<PaginatedThreads>(`/conversations${qs ? `?${qs}` : ""}`, {
        service: "dialer",
      });
    },
    enabled: !!tenantId,
    retry: 1,
    refetchOnWindowFocus: true,
    refetchInterval: 15_000,
  });
}
