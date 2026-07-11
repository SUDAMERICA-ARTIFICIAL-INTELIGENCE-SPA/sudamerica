import {
  buildAlerts,
  buildConversations,
  buildDashboardKpis,
  buildFinancial,
  buildMenuEngineering,
  buildOperational,
  buildRevenue,
  buildRevisiones,
  buildTenant,
  buildTopProducts,
  buildUser,
  buildWeeklyActivity,
} from "@/lib/demo/fixtures";
// ── Resolver demo: (path, rubro) → fixture ─────────────────────────────────
// Chokepoint del modo demo. `api.get` delega aquí cuando el showroom está activo.
// Mapea el path (sin querystring) al builder correcto de `fixtures.ts`. Devuelve
// una Promise para no cambiar el contrato async de `api.get`.
import type { RubroKey } from "@/lib/rubros";

function queryInt(query: string, name: string, fallback: number): number {
  const params = new URLSearchParams(query);
  const raw = params.get(name);
  const n = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(n) ? n : fallback;
}

/** Resuelve el fixture para un GET dado el rubro activo. Determinista. */
export function demoResolve<T>(path: string, rubro: RubroKey): Promise<T> {
  try {
    const [clean, query = ""] = path.split("?");
    return Promise.resolve(route(clean ?? path, query, rubro) as T);
  } catch (err) {
    // Contrato async consistente: los paths no mapeados rechazan la Promise
    // (no lanzan sincrónicamente) igual que un fetch fallido.
    return Promise.reject(err instanceof Error ? err : new Error(String(err)));
  }
}

function route(path: string, query: string, key: RubroKey): unknown {
  // Auth / tenant
  if (path === "/tenants/me") return buildTenant(key);
  if (path === "/auth/me") return buildUser();

  // Métricas
  if (path === "/metricas/dashboard") return buildDashboardKpis(key);
  if (path === "/metricas/revenue") return buildRevenue(key);
  if (path === "/metricas/operativo") return buildOperational(key);
  if (path === "/metricas/productos-top") return buildTopProducts(key, queryInt(query, "limit", 5));
  if (path === "/metricas/financiero") return buildFinancial(key);
  if (path === "/metricas/weekly-activity") return buildWeeklyActivity(key);
  if (path === "/metricas/menu-engineering") return buildMenuEngineering(key);

  // Listados paginados
  if (path === "/ai-conversations")
    return buildConversations(key, queryInt(query, "page_size", 20));
  if (path === "/pendientes") return buildRevisiones(key, queryInt(query, "page_size", 20));
  if (path === "/alertas") return buildAlerts(key, queryInt(query, "page_size", 20));

  throw new Error(`[demo] Sin fixture para GET ${path}`);
}
