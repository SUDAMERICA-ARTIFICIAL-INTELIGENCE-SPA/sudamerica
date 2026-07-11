"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { RevisionAccion } from "@/lib/enums";
import type { ApiResponse, PaginatedResponse, RevisionHumana } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface RevisionFilters {
  page?: number;
  page_size?: number;
  pendiente?: boolean;
  asesor_id?: string;
}

export interface AccionarRevisionDto {
  id: string;
  accion: RevisionAccion;
  notas?: string;
}

export function useRevisionHumana(filters?: RevisionFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["revision-humana", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.pendiente !== undefined) params.set("pendiente", String(filters.pendiente));
      if (filters?.asesor_id) params.set("asesor_id", filters.asesor_id);
      const qs = params.toString();
      return api.get<PaginatedResponse<RevisionHumana>>(`/pendientes${qs ? `?${qs}` : ""}`, {
        service: "callback",
      });
    },
    enabled: !!tenantId,
    refetchOnWindowFocus: true,
    refetchInterval: 10_000,
  });
}

const ACCION_LABELS: Record<RevisionAccion, string> = {
  [RevisionAccion.APROBAR]: "aprobada",
  [RevisionAccion.EDITAR]: "editada",
  [RevisionAccion.RECHAZAR]: "rechazada",
};

export function useAccionarRevision() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, accion, notas }: AccionarRevisionDto) =>
      api.patch<ApiResponse<RevisionHumana>>(
        `/${id}/${accion.toLowerCase()}`,
        { notas },
        { service: "callback" },
      ),
    onSuccess: (_, { accion }) => {
      void qc.invalidateQueries({ queryKey: ["revision-humana", { tenantId }] });
      notifications.show({
        color:
          accion === RevisionAccion.APROBAR
            ? "green"
            : accion === RevisionAccion.EDITAR
              ? "blue"
              : "red",
        title: "Revisión actualizada",
        message: `La conversación fue ${ACCION_LABELS[accion]}.`,
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al revisar", message: err.message });
    },
  });
}
