"use client";

import { AuthProvider } from "@/lib/auth";
import { activateDemo } from "@/lib/demo/state";
import type { ReactNode } from "react";

// Enciende el modo demo al cargar el bundle de este route group (solo cliente).
// Corre antes de los efectos de los componentes → cuando el efecto de
// AuthProvider hidrata, isDemoActive() ya es true y siembra el tenant sintético.
// Fuera de `(showroom)` este módulo nunca se importa → la app real queda intacta.
if (typeof window !== "undefined") {
  activateDemo();
}

/**
 * Layout del Showroom: SIN route guard ni backend. Provee AuthProvider (los
 * hooks de datos usan `useAuth`); en modo demo éste siembra un tenant sintético.
 */
export default function ShowroomLayout({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
