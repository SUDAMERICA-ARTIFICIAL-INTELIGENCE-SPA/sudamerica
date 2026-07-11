"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ClienteSubentidad } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CreateSubentidadDto {
  lead_id: string;
  tipo: string;
  nombre: string;
  datos?: Record<string, unknown>;
}

export interface UpdateSubentidadDto {
  tipo?: string;
  nombre?: string;
  datos?: Record<string, unknown>;
}

/**
 * Sub-entidades del cliente (ficha F6). El backend responde 403 si el rubro no
 * tiene ficha de sub-entidad: montar solo si `subEntidadLabel` está presente.
 */
export function useSubentidades(leadId: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["subentidades", leadId, { tenantId }],
    queryFn: () => api.get<ClienteSubentidad[]>(`/subentidades?lead_id=${leadId}`),
    enabled: !!tenantId && !!leadId,
  });
}

export function useCreateSubentidad(leadId: string) {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateSubentidadDto) => api.post<ClienteSubentidad>("/subentidades", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["subentidades", leadId, { tenantId }] });
      notifications.show({ color: "green", title: "Guardado", message: "Registro agregado." });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}

export function useUpdateSubentidad(leadId: string) {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateSubentidadDto }) =>
      api.patch<ClienteSubentidad>(`/subentidades/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["subentidades", leadId, { tenantId }] });
      notifications.show({ color: "green", title: "Guardado", message: "Cambios guardados." });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}

export function useDeleteSubentidad(leadId: string) {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) => api.delete<ClienteSubentidad>(`/subentidades/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["subentidades", leadId, { tenantId }] });
      notifications.show({ color: "green", title: "Eliminado", message: "Registro eliminado." });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
