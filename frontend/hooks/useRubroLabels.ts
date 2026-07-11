"use client";

import { useTenant } from "@/hooks/useTenant";
import { type RubroDef, getRubroDef, resolveRubro } from "@/lib/rubros";
import { useEffect, useState } from "react";

/** Clave localStorage del override de rubro para desarrollo (switcher del Sidebar). */
export const DEV_RUBRO_OVERRIDE_KEY = "dev_rubro_override";

/**
 * Override de rubro SOLO para desarrollo, gateado por `NEXT_PUBLIC_MOCK_AUTH` (env de
 * build: en prod la condición es `false` literal y el bundler elimina la rama, dejando
 * `resolveRubro` como única fuente). Devuelve null si el flag está OFF o no hay override.
 */
export function readDevRubroOverride(): string | null {
  if (process.env.NEXT_PUBLIC_MOCK_AUTH !== "true") return null;
  return window.localStorage.getItem(DEV_RUBRO_OVERRIDE_KEY);
}

/**
 * Devuelve la definición de rubro del tenant actual (labels, módulos, categorías-semilla).
 *
 * Lee `tenant.config.rubro` vía `useTenant()` y resuelve fail-safe a restaurante, de modo
 * que un tenant sin rubro se comporta igual que hoy. Capa única de etiquetas para la UI:
 * en vez de textos hardcodeados ("Mesa", "Carta") los componentes usan `labels.<primitiva>`.
 *
 * `isLoading` refleja la carga del tenant: mientras es `true` los labels son los del
 * default (restaurante) y el caller puede optar por skeleton en vez de textos provisorios.
 */
export function useRubroLabels(): RubroDef & { isLoading: boolean } {
  const { data: tenant, isLoading } = useTenant();
  // El override dev se lee en efecto (no en render): localStorage no existe en SSR y
  // leerlo en el primer paint divergiría del HTML del servidor (hydration mismatch).
  const [devOverride, setDevOverride] = useState<string | null>(null);
  useEffect(() => {
    setDevOverride(readDevRubroOverride());
  }, []);
  return { ...getRubroDef(devOverride ?? resolveRubro(tenant?.config)), isLoading };
}
