// ── Showroom DEMO state (module singleton) ─────────────────────────────────
// Único punto de verdad del "modo demo". Se activa SOLO desde el route group
// `app/(showroom)/` (su layout llama `activateDemo()` al cargar el bundle). Fuera
// de ese group `active` queda en `false` → la app real y su auth quedan intactas.
//
// `rubro` es el rubro activo del dashboard demo actual; lo fija cada página
// `[rubro]` y lo lee `api.get` (vía el resolver) para servir los fixtures del
// rubro correcto sin tocar la firma `api.get(path)`.
import { RUBRO_DEFAULT, type RubroKey } from "@/lib/rubros";

/** Tenant sintético del modo demo (cualquier valor truthy habilita los hooks). */
export const DEMO_TENANT_ID = "demo-showroom-tenant";

let active = false;
let rubro: RubroKey = RUBRO_DEFAULT;

/** Enciende el modo demo. Idempotente. */
export function activateDemo(): void {
  active = true;
}

/** Fija el rubro activo del dashboard demo. */
export function setDemoRubro(key: RubroKey): void {
  rubro = key;
}

export function isDemoActive(): boolean {
  if (!active) return false;
  // Scope de seguridad: aunque el flag quede encendido en el runtime del tab,
  // el modo demo SOLO aplica bajo `/showroom`. Así una navegación client-side a
  // la app real nunca sirve fixtures. En SSR devolvemos false (los hooks de
  // datos no fetchean en server: `enabled` depende de tenantId de un useEffect).
  if (typeof window === "undefined") return false;
  // Bajo el export estático la app vive en el subpath basePath (`/sudamerica`),
  // así que el pathname real es `<basePath>/showroom/...`. Lo descontamos antes
  // de comparar (en el build real basePath = "" → sin efecto).
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const p = window.location.pathname;
  const rel = basePath && p.startsWith(basePath) ? p.slice(basePath.length) : p;
  return rel.startsWith("/showroom");
}

export function getDemoRubro(): RubroKey {
  return rubro;
}
