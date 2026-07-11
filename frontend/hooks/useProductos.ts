"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ApiResponse, PaginatedResponse, Producto } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ProductosFilters {
  page?: number;
  page_size?: number;
  categoria_id?: string;
  search?: string;
  activo?: boolean;
}

export interface CreateProductoDto {
  nombre: string;
  descripcion?: string;
  precio: number;
  costo?: number;
  stock?: number;
  stock_minimo?: number;
  /** Unidad del precio (kg/m2/…), módulo precio_medida; omitir para venta por unidad. */
  unidad_venta?: string;
  categoria_id?: string;
}

export type UpdateProductoDto = Partial<CreateProductoDto> & {
  activo?: boolean;
  disponible?: boolean;
};

export function useProductos(filters?: ProductosFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["productos", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.page !== undefined) params.set("page", String(filters.page));
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      if (filters?.categoria_id) params.set("categoria_id", filters.categoria_id);
      if (filters?.search) params.set("search", filters.search);
      if (filters?.activo !== undefined) params.set("activo", String(filters.activo));
      const qs = params.toString();
      return api.get<PaginatedResponse<Producto>>(`/productos${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useProducto(id: string | null) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["productos", id, { tenantId }],
    queryFn: () => api.get<Producto>(`/productos/${id}`),
    enabled: !!tenantId && !!id,
  });
}

export function useCreateProducto() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateProductoDto) => api.post<Producto>("/productos", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["productos", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Producto creado",
        message: "Registrado exitosamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al crear producto", message: err.message });
    },
  });
}

export function useUpdateProducto() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateProductoDto }) =>
      api.patch<Producto>(`/productos/${id}`, dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["productos", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Producto actualizado",
        message: "Cambios guardados.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al actualizar", message: err.message });
    },
  });
}

export function useDeleteProducto() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.patch<ApiResponse<Producto>>(`/productos/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["productos", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Producto desactivado",
        message: "El producto fue desactivado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}
