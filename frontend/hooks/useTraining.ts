"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PaginatedResponse } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ── Types ───────────────────────────────────────────────────────────

export interface KnowledgeEntry {
  id: string;
  tenant_id: string;
  type: string;
  title: string;
  content: string;
  priority: number;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeachResponse {
  id: string;
  title: string;
  content: string;
  type: string;
}

export interface TestResponse {
  response: string;
  confidence: number;
  sub_agent: string;
}

// ── Hooks ───────────────────────────────────────────────────────────

/** Fetch all knowledge entries for the current tenant. */
export function useKnowledge() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["knowledge", { tenantId }],
    queryFn: () =>
      api.get<PaginatedResponse<KnowledgeEntry>>("/knowledge", {
        service: "dialer",
      }),
    enabled: !!tenantId,
  });
}

/** Teach the AI new knowledge (POST /knowledge/teach). */
export function useTeach() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (content: string) =>
      api.post<TeachResponse>("/knowledge/teach", { content }, { service: "dialer" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["knowledge"] });
      notifications.show({
        color: "green",
        title: "Conocimiento guardado",
        message: "La IA ahora conoce esta informacion.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al guardar conocimiento",
        message: err.message,
      });
    },
  });
}

/** Test the AI with a message (POST /knowledge/test). */
export function useTestAI() {
  return useMutation({
    mutationFn: (message: string) =>
      api.post<TestResponse>("/knowledge/test", { message }, { service: "dialer" }),
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al probar IA",
        message: err.message,
      });
    },
  });
}

/** Delete a knowledge entry (DELETE /knowledge/{id}). */
export function useDeleteKnowledge() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/knowledge/${id}`, { service: "dialer" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["knowledge"] });
      notifications.show({
        color: "orange",
        title: "Conocimiento eliminado",
        message: "La entrada fue desactivada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al eliminar",
        message: err.message,
      });
    },
  });
}
