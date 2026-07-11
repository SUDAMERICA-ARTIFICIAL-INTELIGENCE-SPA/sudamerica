"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LeadCanal, LeadEstado } from "@/lib/enums";
import type { ApiResponse, Lead, PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface LeadsFilters {
  page?: number;
  page_size?: number;
  estado?: LeadEstado;
  canal?: LeadCanal;
  asesor_id?: string;
  search?: string;
  estado_cliente?: string;
  order_by?: string;
}

export interface CreateLeadDto {
  nombre: string;
  email?: string;
  telefono?: string;
  canal: LeadCanal;
  valor_estimado?: number;
  asesor_id?: string;
  sector_data?: Record<string, unknown>;
}

export type UpdateLeadDto = Partial<CreateLeadDto> & {
  estado?: LeadEstado;
  activo?: boolean;
};

export function useLeads(filters?: LeadsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["leads", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.estado) params.set("estado", filters.estado);
      if (filters?.canal) params.set("canal", filters.canal);
      if (filters?.asesor_id) params.set("asesor_id", filters.asesor_id);
      if (filters?.search) params.set("search", filters.search);
      if (filters?.estado_cliente) params.set("estado_cliente", filters.estado_cliente);
      if (filters?.order_by) params.set("order_by", filters.order_by);
      const qs = params.toString();
      return api.get<PaginatedResponse<Lead>>(`/leads${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useLead(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["leads", id, { tenantId }],
    queryFn: () => api.get<Lead>(`/leads/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useCreateLead() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateLeadDto) => api.post<Lead>("/leads", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leads", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Cliente creado",
        message: "Cliente registrado exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al crear cliente", message: err.message });
    },
  });
}

export function useUpdateLead() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateLeadDto }) =>
      api.patch<Lead>(`/leads/${id}`, dto),
    onSuccess: (_, { id }) => {
      void qc.invalidateQueries({ queryKey: ["leads", { tenantId }] });
      void qc.invalidateQueries({ queryKey: ["leads", id] });
      notifications.show({
        color: "green",
        title: "Cliente actualizado",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al actualizar", message: err.message });
    },
  });
}

export function useDeleteLead() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) => api.patch<ApiResponse<Lead>>(`/leads/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leads", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Cliente desactivado",
        message: "El cliente fue desactivado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
