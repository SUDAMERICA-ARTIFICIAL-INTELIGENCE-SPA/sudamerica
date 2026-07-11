"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LeadInteraction, PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CreateInteractionDto {
  tipo: string;
  descripcion: string;
}

export function useLeadInteractions(leadId: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["lead-interactions", leadId, { tenantId }],
    queryFn: () =>
      api.get<PaginatedResponse<LeadInteraction>>(`/leads/${leadId}/interactions?page_size=50`),
    enabled: !!tenantId && !!leadId,
  });
}

export function useCreateInteraction(leadId: string) {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateInteractionDto) =>
      api.post<LeadInteraction>(`/leads/${leadId}/interactions`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["lead-interactions", leadId, { tenantId }] });
      notifications.show({
        color: "green",
        title: "Interacción registrada",
        message: "Actividad guardada en el timeline.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
