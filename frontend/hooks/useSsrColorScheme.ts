"use client";

import { useComputedColorScheme } from "@mantine/core";
import { useEffect, useState } from "react";

/**
 * Color scheme SSR-safe: devuelve "dark" (el default que renderiza el servidor)
 * durante SSR y el PRIMER render de cliente, y el valor real recién tras el mount.
 *
 * Necesario porque Mantine lee localStorage sincrónicamente al inicializar el
 * provider en cliente (`getInitialValueInEffect` solo difiere la media query del
 * SO para "auto", NO el valor persistido): con "light" guardado, leer el scheme
 * en render diverge del HTML del servidor → hydration mismatch.
 */
export function useSsrColorScheme(): "light" | "dark" {
  const computed = useComputedColorScheme("dark", { getInitialValueInEffect: true });
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  return mounted ? computed : "dark";
}
