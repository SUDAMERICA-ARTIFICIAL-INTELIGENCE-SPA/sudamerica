"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiResponse, Categoria, PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CreateCategoriaDto {
  nombre: string;
}

export type UpdateCategoriaDto = Partial<CreateCategoriaDto> & { activo?: boolean };

export function useCategorias() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["categorias", { tenantId }],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Categoria>>("/categorias");
      return res.data ?? [];
    },
    enabled: !!tenantId,
  });
}

export function useCreateCategoria() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateCategoriaDto) => api.post<ApiResponse<Categoria>>("/categorias", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["categorias", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Categoría creada",
        message: "Registrada exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al crear categoría", message: err.message });
    },
  });
}

export function useUpdateCategoria() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateCategoriaDto }) =>
      api.patch<ApiResponse<Categoria>>(`/categorias/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["categorias", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Categoría actualizada",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al actualizar", message: err.message });
    },
  });
}

export function useDeleteCategoria() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.patch<ApiResponse<Categoria>>(`/categorias/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["categorias", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Categoría desactivada",
        message: "La categoría fue desactivada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
