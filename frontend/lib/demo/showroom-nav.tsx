"use client";

// ── Base-path de navegación del showroom ───────────────────────────────────
// La app real vive en rutas autenticadas (`/contactos/directorio`); la vitrina
// las re-monta bajo `/showroom/<rubro>/...`. Para reutilizar el Sidebar y el
// CommandPalette REALES sin bifurcarlos, exponemos un "base" por contexto que
// esos componentes anteponen a cada href. Fuera del showroom el base es "" y el
// comportamiento queda idéntico. SSR-safe: el valor lo fija el provider server-
// renderizado (no lee window), así el href de SSR == el de cliente (sin mismatch).
import { createContext, useCallback, useContext } from "react";
import type { ReactNode } from "react";

const NavBaseContext = createContext<string>("");

export function ShowroomNavProvider({ base, children }: { base: string; children: ReactNode }) {
  return <NavBaseContext.Provider value={base}>{children}</NavBaseContext.Provider>;
}

/** Base actual ("" en la app real, "/showroom/<rubro>" en la vitrina). */
export function useNavBase(): string {
  return useContext(NavBaseContext);
}

/** Devuelve un mapper `href → base+href` (solo prefija rutas absolutas internas). */
export function useWithBase(): (href: string) => string {
  const base = useNavBase();
  return useCallback(
    (href: string) => (base && href.startsWith("/") ? `${base}${href}` : href),
    [base],
  );
}
