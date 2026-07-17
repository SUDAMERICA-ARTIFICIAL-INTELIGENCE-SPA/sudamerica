"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Tenant } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";

/** Props que el orquestador pasa a cada paso del wizard. */
export interface OnboardingStepProps {
  /** Avanza al siguiente paso (el paso ya persistió lo suyo). */
  goNext: () => void;
  /** Retrocede al paso anterior (no-op en el primero). */
  goBack: () => void;
}

/** Convierte un color del design system (#RRGGBB) a rgba con alpha custom. */
export function withAlpha(hex: string, alpha: number): string {
  const r = Number.parseInt(hex.slice(1, 3), 16);
  const g = Number.parseInt(hex.slice(3, 5), 16);
  const b = Number.parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Timestamp ISO del momento actual (marca de progreso del onboarding). */
export function nowIso(): string {
  return new Date().toISOString();
}

interface SaveOnboardingVars {
  /** Campos a mergear en `tenants.config` (deep-merge en backend). */
  config?: Record<string, unknown>;
  /** Marcas de progreso a mergear en `config.onboarding`. */
  onboarding?: Record<string, string | boolean>;
  /** Copy del toast de éxito (correcto por paso). Sin él, no muestra toast. */
  successMessage?: string;
}

/**
 * Persistencia incremental del wizard. Un solo PATCH `/tenants/me` por paso: mergea los
 * campos de negocio y la marca de progreso en `config` (el backend hace deep-merge, así que
 * cada paso solo envía lo suyo). Copy del toast controlado por el caller para no reusar el
 * genérico "Negocio actualizado" en pasos como Rubro o WhatsApp.
 */
export function useSaveOnboarding() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: SaveOnboardingVars) =>
      api.patch<Tenant>("/tenants/me", {
        config: {
          ...(vars.config ?? {}),
          onboarding: { required: true, ...(vars.onboarding ?? {}) },
        },
      }),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
      if (vars.successMessage) {
        notifications.show({ color: "green", message: vars.successMessage });
      }
    },
    onError: (error: Error) => {
      notifications.show({
        color: "red",
        title: "No se pudo guardar",
        message: error.message,
      });
    },
  });
}
