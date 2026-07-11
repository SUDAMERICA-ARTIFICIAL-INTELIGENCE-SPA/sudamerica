"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { QuoteEstado } from "@/lib/enums";
import type { PaginatedResponse, QuoteEstimate } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CreateQuoteDto {
  lead_id: string;
  notas?: string;
  total: number;
}

export interface UpdateQuoteDto {
  estado?: QuoteEstado;
  notas?: string;
}

export function useQuotes(leadId: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["quotes", leadId, { tenantId }],
    queryFn: () =>
      api.get<PaginatedResponse<QuoteEstimate>>(`/quotes?lead_id=${leadId}&page_size=20`),
    enabled: !!tenantId && !!leadId,
  });
}

export function useCreateQuote() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateQuoteDto) => api.post<QuoteEstimate>("/quotes", dto),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: ["quotes", vars.lead_id, { tenantId }] });
      notifications.show({
        color: "green",
        title: "Cotización creada",
        message: "Presupuesto generado correctamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear cotización",
        message: err.message,
      });
    },
  });
}

export function useUpdateQuote() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateQuoteDto }) =>
      api.patch<QuoteEstimate>(`/quotes/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["quotes", { tenantId }] });
      notifications.show({
        color: "teal",
        title: "Cotización actualizada",
        message: "Estado actualizado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al actualizar", message: err.message });
    },
  });
}
