"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Comanda, KDSView, PaginatedResponse } from "@/lib/types";
import { useUiStore } from "@/stores/ui-store";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ComandasFilters {
  page?: number;
  page_size?: number;
  estado?: string;
  tipo_entrega?: string;
  canal_origen?: string;
}

export interface ComandaItemDto {
  producto_id: string;
  cantidad?: number;
  modifiers_json?: Array<{ modifier_id: string }>;
  notas?: string;
}

export interface CreateComandaDto {
  cliente_id?: string;
  tipo_entrega: string;
  numero_mesa?: number;
  canal_origen: string;
  notas?: string;
  prioridad?: number;
  tiempo_estimado_min?: number;
  items: ComandaItemDto[];
}

export function useComandas(filters?: ComandasFilters) {
  const { tenantId } = useAuth();
  const activeSucursalId = useUiStore((s) => s.activeSucursalId);

  return useQuery({
    queryKey: ["comandas", { tenantId, activeSucursalId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined)
        params.set("page_size", String(filters.page_size));
      if (filters?.estado) params.set("estado", filters.estado);
      if (filters?.tipo_entrega) params.set("tipo_entrega", filters.tipo_entrega);
      if (filters?.canal_origen) params.set("canal_origen", filters.canal_origen);
      if (activeSucursalId) params.set("sucursal_id", activeSucursalId);
      const qs = params.toString();
      return api.get<PaginatedResponse<Comanda>>(
        `/comandas${qs ? `?${qs}` : ""}`
      );
    },
    enabled: !!tenantId,
  });
}

export function useKDS(options?: { wsConnected?: boolean }) {
  const { tenantId } = useAuth();
  const activeSucursalId = useUiStore((s) => s.activeSucursalId);
  const wsConnected = options?.wsConnected ?? false;

  return useQuery({
    queryKey: ["comandas", "kds", { tenantId, activeSucursalId }],
    queryFn: () => {
      const params = activeSucursalId ? `?sucursal_id=${activeSucursalId}` : "";
      return api.get<KDSView>(`/comandas/kds${params}`);
    },
    enabled: !!tenantId,
    refetchInterval: wsConnected ? false : 5000,
  });
}

export function useComanda(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["comandas", id, { tenantId }],
    queryFn: () => api.get<Comanda>(`/comandas/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useCreateComanda() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (dto: CreateComandaDto) =>
      api.post<Comanda>("/comandas", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["comandas"] });
      notifications.show({
        color: "green",
        title: "Comanda creada",
        message: "La orden fue enviada a cocina.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear comanda",
        message: err.message,
      });
    },
  });
}

export function useTransitionComanda() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      api.patch<Comanda>(`/comandas/${id}/estado`, { estado }),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["comandas"] });
      const labels: Record<string, string> = {
        EN_COCINA: "En cocina",
        LISTO: "Listo para entregar",
        ENTREGADO: "Entregado",
        CANCELADO: "Cancelado",
      };
      notifications.show({
        color: variables.estado === "CANCELADO" ? "red" : "green",
        title: "Estado actualizado",
        message: labels[variables.estado] ?? variables.estado,
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al cambiar estado",
        message: err.message,
      });
    },
  });
}

/** Fetch recent completed (ENTREGADO + CANCELADO) comandas (last 24h). */
export function useTodayHistory() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["comandas", "today-history", { tenantId }],
    queryFn: async () => {
      // Use 24h window instead of midnight to avoid timezone edge cases
      const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

      const [entregados, cancelados] = await Promise.all([
        api.get<PaginatedResponse<Comanda>>(
          `/comandas?estado=ENTREGADO&fecha_desde=${since}&page_size=50`
        ),
        api.get<PaginatedResponse<Comanda>>(
          `/comandas?estado=CANCELADO&fecha_desde=${since}&page_size=50`
        ),
      ]);
      return {
        entregados: entregados.data ?? [],
        cancelados: cancelados.data ?? [],
      };
    },
    enabled: !!tenantId,
    refetchInterval: 10000,
  });
}

export function useDeleteComanda() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/comandas/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["comandas"] });
      notifications.show({
        color: "orange",
        title: "Comanda eliminada",
        message: "La comanda fue eliminada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
