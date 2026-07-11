"use client";

import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { SubAgenteType } from "@/lib/enums";
import type { AgenteConfig } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface UpdateAgenteConfigDto {
  activo?: boolean;
  config?: Record<string, unknown>;
}

/** Raw shape returned by `GET /api/v1/ai/config`. */
interface BackendAgenteConfig {
  id: string;
  tenant_id: string;
  sub_agentes_activos: Record<string, boolean> | null;
  activo: boolean;
  [key: string]: unknown;
}

const ALL_TIPOS = Object.values(SubAgenteType);

/** Transform backend single-config into per-sub-agent array. */
function toSubAgentArray(raw: BackendAgenteConfig): AgenteConfig[] {
  const subs = raw.sub_agentes_activos ?? {};
  return ALL_TIPOS.map((tipo) => ({
    id: `${raw.id}-${tipo}`,
    tenant_id: String(raw.tenant_id),
    tipo,
    activo: Boolean(subs[tipo]),
    config: {},
    updated_at: new Date().toISOString(),
  }));
}

export function useAgenteConfigs() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["agente-configs", { tenantId }],
    queryFn: async () => {
      try {
        const raw = await api.get<BackendAgenteConfig>("/config", { service: "dialer" });
        return toSubAgentArray(raw);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return [];
        throw err;
      }
    },
    enabled: !!tenantId,
  });
}

export function useUpdateAgenteConfig() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: async ({ tipo, dto }: { tipo: SubAgenteType; dto: UpdateAgenteConfigDto }) => {
      // Read current config, update sub_agentes_activos for this tipo
      const raw = await api.get<BackendAgenteConfig>("/config", { service: "dialer" });
      const subs = { ...(raw.sub_agentes_activos ?? {}) };
      if (dto.activo !== undefined) subs[tipo] = dto.activo;
      return api.patch<BackendAgenteConfig>("/config", { sub_agentes_activos: subs }, {
        service: "dialer",
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agente-configs", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Agente actualizado",
        message: "Configuración guardada.",
      });
    },
    onError: (err: Error) => {
      const isAuthError = err instanceof ApiError && err.status === 401;
      if (isAuthError && typeof window !== "undefined") {
        window.location.href = "/login";
        return;
      }
      notifications.show({
        color: "red",
        title: "Error",
        message: isAuthError
          ? "Sesión expirada. Redirigiendo al login..."
          : "No se pudo cambiar la configuración.",
      });
    },
  });
}

/** Fetch the raw backend config (not transformed into sub-agent array). */
export function useAgenteConfigRaw() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["agente-config-raw", { tenantId }],
    queryFn: async () => {
      try {
        return await api.get<BackendAgenteConfig>("/config", { service: "dialer" });
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled: !!tenantId,
  });
}

/** Update agent profile fields (nombre_agente, personalidad). */
export function useUpdateAgentProfile() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (dto: { nombre_agente?: string; personalidad?: string }) =>
      api.patch<BackendAgenteConfig>("/config", dto, { service: "dialer" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agente-config-raw", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Perfil actualizado",
        message: "El perfil del agente fue guardado.",
      });
    },
    onError: (err: Error) => {
      notifications.show({ color: "red", title: "Error", message: err.message });
    },
  });
}

/** Update instrucciones_disponibilidad field on agente_config. */
export function useUpdateAvailabilityInstructions() {
  const qc = useQueryClient();
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: (instrucciones: string) =>
      api.patch<BackendAgenteConfig>(
        "/config",
        { instrucciones_disponibilidad: instrucciones },
        { service: "dialer" },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agente-config-raw", { tenantId }] });
      notifications.show({
        color: "green",
        title: "Instrucciones guardadas",
        message: "Las reglas de disponibilidad se actualizaron.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al guardar instrucciones",
        message: err.message,
      });
    },
  });
}
