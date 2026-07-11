"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LeadStageHistory, PaginatedResponse } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function useLeadStageHistory(leadId: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["lead-stage-history", leadId, { tenantId }],
    queryFn: () =>
      api.get<PaginatedResponse<LeadStageHistory>>(`/leads/${leadId}/stage-history?page_size=20`),
    enabled: !!tenantId && !!leadId,
  });
}
