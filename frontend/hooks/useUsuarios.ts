"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/enums";
import type { ApiResponse, PaginatedResponse, Usuario } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

/** NOTE: Users are created via auth flow — no create mutation. */
export interface UpdateUsuarioDto {
  nombre?: string;
  role?: UserRole;
  activo?: boolean;
}

export interface CreateUsuarioDto {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  role: UserRole;
  sucursal_id?: string | null;
}

export function useUsuarios() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["usuarios", { tenantId }],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Usuario>>("/usuarios");
      return res.data ?? [];
    },
    enabled: !!tenantId,
  });
}

export function useUpdateUsuario() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateUsuarioDto }) =>
      api.patch<ApiResponse<Usuario>>(`/usuarios/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["usuarios", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Usuario actualizado",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al actualizar usuario",
        message: err.message,
      });
    },
  });
}

export function useCreateUsuario() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateUsuarioDto) =>
      api.post<ApiResponse<Usuario>>("/usuarios", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["usuarios", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Usuario creado",
        message: "El usuario fue invitado exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear usuario",
        message: err.message,
      });
    },
  });
}

export function useUpdateUsuarioRole() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) =>
      api.patch<ApiResponse<Usuario>>(`/usuarios/${id}`, { role }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["usuarios", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Rol actualizado",
        message: "El rol del usuario fue cambiado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al cambiar rol",
        message: err.message,
      });
    },
  });
}

export function useDeactivateUsuario() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.patch<ApiResponse<Usuario>>(`/usuarios/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["usuarios", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Usuario desactivado",
        message: "El usuario fue desactivado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al desactivar usuario",
        message: err.message,
      });
    },
  });
}
