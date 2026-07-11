"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Sucursal } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function useSucursales() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["sucursales", { tenantId }],
    queryFn: () => api.get<Sucursal[]>("/sucursales"),
    enabled: !!tenantId,
  });
}

export function useCreateSucursal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      body: Pick<Sucursal, "nombre"> &
        Partial<
          Pick<
            Sucursal,
            | "direccion"
            | "telefono"
            | "horario"
            | "zona_delivery"
            | "latitud"
            | "longitud"
            | "config"
          >
        >,
    ) => api.post<Sucursal>("/sucursales", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sucursales"] });
      notifications.show({
        color: "green",
        title: "Sucursal creada",
        message: "La nueva sucursal se creó correctamente.",
      });
    },
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "Error al crear sucursal",
        message: error.message,
      });
    },
  });
}

export function useUpdateSucursal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: { id: string } & Partial<
      Pick<
        Sucursal,
        | "nombre"
        | "direccion"
        | "telefono"
        | "horario"
        | "zona_delivery"
        | "latitud"
        | "longitud"
        | "config"
      >
    >) => api.patch<Sucursal>(`/sucursales/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sucursales"] });
      notifications.show({
        color: "green",
        title: "Sucursal actualizada",
        message: "Los cambios se guardaron correctamente.",
      });
    },
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "Error al actualizar sucursal",
        message: error.message,
      });
    },
  });
}

export function useDeactivateSucursal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete<Sucursal>(`/sucursales/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sucursales"] });
      notifications.show({
        color: "green",
        title: "Sucursal desactivada",
        message: "La sucursal fue desactivada correctamente.",
      });
    },
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "Error al desactivar sucursal",
        message: error.message,
      });
    },
  });
}
