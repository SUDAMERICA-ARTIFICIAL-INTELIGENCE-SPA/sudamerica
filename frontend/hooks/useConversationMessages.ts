"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";

export interface ConversationMessage {
  id: string;
  role: string;
  content: string;
  canal: string | null;
  tokens_used: number | null;
  modelo: string | null;
  session_id: string | null;
  media_url: string | null;
  media_type: string | null;
  created_at: string;
}

interface PaginatedMessages {
  data: ConversationMessage[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isValidLeadId(id: string | null): id is string {
  return id != null && UUID_RE.test(id);
}

export function useConversationMessages(leadId: string | null, page = 1) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["conversation-messages", leadId, page, { tenantId }],
    queryFn: () =>
      api.get<PaginatedMessages>(
        `/conversations/${encodeURIComponent(leadId!)}/messages?page=${page}&page_size=50`,
        { service: "dialer" },
      ),
    enabled: !!tenantId && isValidLeadId(leadId),
    refetchOnWindowFocus: true,
    refetchInterval: 5_000,
  });
}
