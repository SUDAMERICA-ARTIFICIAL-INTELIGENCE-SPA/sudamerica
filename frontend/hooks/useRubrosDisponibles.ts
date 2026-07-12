"use client";

import {
  type RubroOption,
  fetchRubrosDisponibles,
  mergeRubroOptions,
} from "@/lib/rubros-live";
import { RUBRO_OPTIONS } from "@/lib/rubros";
import { useEffect, useState } from "react";

/**
 * Opciones de rubro para selectores de onboarding/registro/admin, incluyendo los rubros
 * `origen='runtime'` que NO están en el fixture compilado (Fase C, Paso 6).
 *
 * Arranca con el baseline ESTÁTICO de código (`RUBRO_OPTIONS`) para que el primer paint —y el
 * SSR— siempre muestren el roster de código sin depender de la red (fail-open). En un efecto
 * consulta el set vivo por API y fusiona los rubros runtime encima. Si la API falla, se conserva
 * el baseline (la UI nunca queda vacía). `isLoading` refleja la carga del set vivo.
 */
export function useRubrosDisponibles(): {
  options: RubroOption[];
  isLoading: boolean;
} {
  const [options, setOptions] = useState<RubroOption[]>(() => [...RUBRO_OPTIONS]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelado = false;
    fetchRubrosDisponibles()
      .then((live) => {
        if (!cancelado) setOptions(mergeRubroOptions(live));
      })
      .catch(() => {
        // Fail-open: se conserva el baseline estático ya presente en el estado inicial.
      })
      .finally(() => {
        if (!cancelado) setIsLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  return { options, isLoading };
}
