"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CalendarEventTipo } from "@/lib/enums";
import type { ApiResponse, CalendarEvent, PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CalendarFilters {
  lead_id?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  page_size?: number;
}

export interface CreateCalendarEventDto {
  titulo: string;
  descripcion?: string;
  lead_id?: string;
  fecha_inicio: string;
  fecha_fin?: string;
  tipo: CalendarEventTipo;
}

export function useCalendarEvents(filters?: CalendarFilters) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["calendar-events", { tenantId, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.lead_id) params.set("lead_id", filters.lead_id);
      if (filters?.fecha_desde) params.set("fecha_desde", filters.fecha_desde);
      if (filters?.fecha_hasta) params.set("fecha_hasta", filters.fecha_hasta);
      if (filters?.page_size !== undefined) params.set("page_size", String(filters.page_size));
      const qs = params.toString();
      return api.get<PaginatedResponse<CalendarEvent>>(`/calendar-events${qs ? `?${qs}` : ""}`);
    },
    enabled: !!tenantId,
  });
}

export function useCreateCalendarEvent() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: CreateCalendarEventDto) => api.post<CalendarEvent>("/calendar-events", dto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["calendar-events", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Evento creado",
        message: "Evento agendado correctamente.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al crear evento", message: err.message });
    },
  });
}

export function useDeleteCalendarEvent() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (id: string) =>
      api.patch<ApiResponse<CalendarEvent>>(`/calendar-events/${id}`, { activo: false }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["calendar-events", { tenantId }] });
      notifications.show({
        color: "orange",
        title: "Evento eliminado",
        message: "El evento fue eliminado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error al eliminar", message: err.message });
    },
  });
}
