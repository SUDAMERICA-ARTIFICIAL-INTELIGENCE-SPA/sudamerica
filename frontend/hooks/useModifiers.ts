"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ModifierGroup, PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ModifierGroupsFilters {
  page?: number;
  page_size?: number;
  nombre?: string;
}

export interface CreateModifierDto {
  nombre: string;
  precio_delta?: number;
  orden?: number;
}

export interface CreateModifierGroupDto {
  nombre: string;
  tipo: string;
  obligatorio?: boolean;
  max_selecciones?: number | null | undefined;
  modifiers?: CreateModifierDto[] | undefined;
}

export type UpdateModifierGroupDto = Partial<Omit<CreateModifierGroupDto, "modifiers">>;

export function useModifierGroups(filters?: ModifierGroupsFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["modifier-groups", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.nombre) params.set("nombre", filters.nombre);
      const qs = params.toString();
      return api.get<PaginatedResponse<ModifierGroup>>(
        `/modifier-groups${qs ? `?${qs}` : ""}`
      );
    },
    enabled: !!tenantId,
  });
}

export function useModifierGroup(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["modifier-groups", id, { tenantId }],
    queryFn: () => api.get<ModifierGroup>(`/modifier-groups/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useProductModifierGroups(productoId: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["modifier-groups", "producto", productoId, { tenantId }],
    queryFn: () =>
      api.get<ModifierGroup[]>(`/modifier-groups/productos/${productoId}`),
    enabled: !!tenantId && !!productoId,
  });
}

export function useCreateModifierGroup() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateModifierGroupDto) =>
      api.post<ModifierGroup>("/modifier-groups", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["modifier-groups"] });
      notifications.show({
        color: "green",
        title: "Grupo de modificadores creado",
        message: "Registrado exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear grupo",
        message: err.message,
      });
    },
  });
}

export function useUpdateModifierGroup() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateModifierGroupDto }) =>
      api.patch<ModifierGroup>(`/modifier-groups/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["modifier-groups"] });
      notifications.show({
        color: "green",
        title: "Grupo actualizado",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al actualizar",
        message: err.message,
      });
    },
  });
}

export function useDeleteModifierGroup() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/modifier-groups/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["modifier-groups"] });
      notifications.show({
        color: "orange",
        title: "Grupo eliminado",
        message: "El grupo fue desactivado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}

export function useAssignProductModifierGroups() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      productoId,
      modifierGroupIds,
    }: {
      productoId: string;
      modifierGroupIds: string[];
    }) =>
      api.patch(`/modifier-groups/productos/${productoId}`, {
        modifier_group_ids: modifierGroupIds,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["modifier-groups"] });
      notifications.show({
        color: "green",
        title: "Modificadores asignados",
        message: "Grupos asignados al producto.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
