"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiResponse, Mesa, PaginatedResponse } from "@/lib/types";
import { useUiStore } from "@/stores/ui-store";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CreateMesaDto {
  numero: number;
  nombre?: string | null;
  capacidad: number;
  sucursal_id?: string | null;
}

export interface UpdateMesaDto {
  numero?: number;
  nombre?: string | null;
  capacidad?: number;
  activo?: boolean;
}

export function useMesas(sucursalIdOverride?: string | null) {
  const { tenantId } = useAuth();
  const globalSucursalId = useUiStore((s) => s.activeSucursalId);
  const sucursalId = sucursalIdOverride !== undefined ? sucursalIdOverride : globalSucursalId;

  return useQuery({
    queryKey: ["mesas", { tenantId, sucursalId }],
    queryFn: async () => {
      const params = sucursalId ? `?sucursal_id=${sucursalId}` : "";
      const res = await api.get<PaginatedResponse<Mesa>>(`/mesas${params}`);
      return res.data ?? [];
    },
    enabled: !!tenantId,
  });
}

export function useCreateMesa() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateMesaDto) =>
      api.post<ApiResponse<Mesa>>("/mesas", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["mesas", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Mesa creada",
        message: "La mesa fue agregada exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear mesa",
        message: err.message,
      });
    },
  });
}

export function useUpdateMesa() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateMesaDto }) =>
      api.patch<ApiResponse<Mesa>>(`/mesas/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["mesas", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Mesa actualizada",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al actualizar mesa",
        message: err.message,
      });
    },
  });
}

export function useDeleteMesa() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.delete<ApiResponse<Mesa>>(`/mesas/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["mesas", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Mesa eliminada",
        message: "La mesa fue eliminada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al eliminar mesa",
        message: err.message,
      });
    },
  });
}

export function useRegenerateMesaQr() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (mesaId: string) =>
      api.post<ApiResponse<Mesa>>(`/mesas/${mesaId}/regenerate-qr`, {}),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["mesas", { tenantId }] });
      notifications.show({
        color: "green",
        title: "QR regenerado",
        message: "Se genero un nuevo codigo QR para la mesa.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al regenerar QR",
        message: err.message,
      });
    },
  });
}
