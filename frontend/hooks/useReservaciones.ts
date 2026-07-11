"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface Reservacion {
  id: string;
  tenant_id: string;
  lead_id: string | null;
  mesa_id: string | null;
  fecha_reserva: string;
  hora_inicio: string;
  hora_fin: string;
  cantidad_personas: number;
  nombre_cliente: string;
  rut: string | null;
  email: string | null;
  telefono: string | null;
  estado: string;
  notas: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

interface PaginatedReservaciones {
  data: Reservacion[];
  meta: { total: number; page: number; page_size: number; total_pages: number };
}

export function useReservaciones(fecha?: string, estado?: string, page = 1) {
  const { tenantId } = useAuth();

  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", "20");
  if (fecha) params.set("fecha", fecha);
  if (estado) params.set("estado", estado);

  return useQuery({
    queryKey: ["reservaciones", { tenantId, fecha, estado, page }],
    queryFn: () =>
      api.get<PaginatedReservaciones>(`/reservaciones?${params.toString()}`),
    enabled: !!tenantId,
  });
}

export function useCancelReservacion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete<Reservacion>(`/reservaciones/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reservaciones"] });
    },
  });
}

export function useUpdateReservacion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; estado?: string; notas?: string }) =>
      api.patch<Reservacion>(`/reservaciones/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reservaciones"] });
    },
  });
}
