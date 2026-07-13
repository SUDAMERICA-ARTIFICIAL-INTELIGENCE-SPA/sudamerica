// ── Resolver demo: (path, rubro) → fixture ─────────────────────────────────
// Chokepoint del modo showroom. `api.get` delega aquí cuando el showroom está
// activo. Estrategia en tres capas, por prioridad:
//
//   1. SNAPSHOT (rubro héroe `cosmetica_belleza`): datos REALES capturados del
//      backend seedeado (`tools/snapshot_demo_fixtures.mjs`). Fieles 1:1 al
//      dashboard logueado. Es la cuenta "que quedó bien" (aura-demo).
//   2. RESKIN (cualquier otro rubro): el mismo snapshot, transformado de forma
//      determinista — montos escalados al perfil económico del sector del rubro,
//      identidad de tenant propia. Cubre las 49 subs para TODOS los rubros sin
//      "fixture faltante", con cifras coherentes entre endpoints (mismo factor).
//   3. SINTÉTICO / VACÍO: endpoints sin snapshot (los que el backend real 404ea:
//      tenant-economics, calendar, quotes, …) → builders sintéticos donde aporta,
//      o sobre paginado vacío (fiel al backend real, que tampoco los sirve).
//
// El querystring se ignora para el match (se re-pagina con `reslice`). Todo es
// SSR-safe y determinista: sin Date.now/Math.random/new Date en runtime.
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
import { SECTOR_PROFILE } from "@/lib/demo/gen";
import type { SnapshotEntry } from "@/lib/demo/snapshot-types";
import { COSMETICA_SNAPSHOTS } from "@/lib/demo/snapshots/cosmetica_belleza/store.generated";
import { RUBROS, type RubroKey } from "@/lib/rubros";

/** Rubro cuya vitrina es 100% fiel (snapshots reales del backend seedeado). */
const HERO: RubroKey = "cosmetica_belleza";

// ── Índice de snapshots: exactos + patrones con {id} ───────────────────────
const EXACT = new Map<string, SnapshotEntry>();
const PATTERNS: { re: RegExp; entry: SnapshotEntry }[] = [];
for (const entry of COSMETICA_SNAPSHOTS) {
  const base = entry.serve.split("?")[0] ?? entry.serve;
  if (base.includes("{")) {
    // `/leads/{id}/interactions` → empareja cualquier id (vitrina read-only).
    const re = new RegExp(`^${base.replace(/\{[^}]+\}/g, "[^/]+")}$`);
    PATTERNS.push({ re, entry });
  } else {
    EXACT.set(base, entry);
  }
}

function matchSnapshot(clean: string): SnapshotEntry | undefined {
  const hit = EXACT.get(clean);
  if (hit) return hit;
  return PATTERNS.find((p) => p.re.test(clean))?.entry;
}

// ── Utilidades de query / paginación ───────────────────────────────────────
function queryInt(query: string, name: string, fallback: number): number {
  const raw = new URLSearchParams(query).get(name);
  const n = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(n) ? n : fallback;
}

interface Paginated {
  data: unknown[];
  meta: { total: number; page: number; page_size: number; total_pages: number };
}

function isPaginated(v: unknown): v is Paginated {
  return (
    typeof v === "object" &&
    v !== null &&
    Array.isArray((v as { data?: unknown }).data) &&
    typeof (v as { meta?: unknown }).meta === "object"
  );
}

/** Re-pagina/recorta el snapshot según el query que pidió el hook. */
function reslice(data: unknown, query: string): unknown {
  if (isPaginated(data)) {
    const rows = data.data;
    const page = Math.max(1, queryInt(query, "page", 1));
    const pageSize = Math.max(1, queryInt(query, "page_size", rows.length || 1));
    const start = (page - 1) * pageSize;
    return {
      ...data,
      data: rows.slice(start, start + pageSize),
      meta: {
        total: rows.length,
        page,
        page_size: pageSize,
        total_pages: Math.max(1, Math.ceil(rows.length / pageSize)),
      },
    };
  }
  if (Array.isArray(data)) {
    const limit = queryInt(query, "limit", Number.NaN);
    return Number.isFinite(limit) ? data.slice(0, limit) : data;
  }
  return data;
}

// ── Reskin determinista por rubro (capa 2) ─────────────────────────────────
// Escala los campos monetarios al perfil de sector del rubro. Deja intactos
// conteos, ids, fechas, porcentajes y strings → shapes idénticas al snapshot.
const MONEY_KEY =
  /(monto|precio|costo|revenue|cogs|saldo|cxp|importe|valor|ingreso|egreso|ventas_mes|meta_mes|cobrad|pendiente|comprado|ahorro|ticket|_usd|_clp|_total$|^total_[a-z]*(?:cobrado|comprado|ventas|revenue)?)/i;
const NON_MONEY_KEY = /(pct|porcentaje|_pages|page_size|page$|count|cantidad|unidades|_id$|^id$)/i;

function midTicket(key: RubroKey): number {
  const def = RUBROS[key];
  if (!def) return midTicket(HERO); // rubro inesperado → escala neutra (no crash)
  const p = SECTOR_PROFILE[def.sector];
  return (p.ticket[0] + p.ticket[1]) / 2;
}

/** Factor de escala monetaria del rubro respecto al héroe. Determinista. */
function moneyScale(rubro: RubroKey): number {
  const s = midTicket(rubro) / midTicket(HERO);
  // Acota para evitar magnitudes absurdas en la vitrina.
  return Math.min(400, Math.max(0.05, s));
}

function reskinValue(key: string, value: unknown, scale: number): unknown {
  if (typeof value === "number" && MONEY_KEY.test(key) && !NON_MONEY_KEY.test(key)) {
    const scaled = value * scale;
    // Redondeo "presentable" según magnitud.
    const step = scaled >= 1_000_000 ? 10_000 : scaled >= 10_000 ? 1000 : scaled >= 100 ? 10 : 1;
    return Math.round(scaled / step) * step;
  }
  return value;
}

function deepReskin(node: unknown, scale: number, key = ""): unknown {
  if (Array.isArray(node)) return node.map((n) => deepReskin(n, scale, key));
  if (node !== null && typeof node === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(node)) {
      out[k] =
        v !== null && typeof v === "object" ? deepReskin(v, scale, k) : reskinValue(k, v, scale);
    }
    return out;
  }
  return reskinValue(key, node, scale);
}

// ── Capa 3: sintético / vacío para endpoints sin snapshot ──────────────────
function emptyPage(query: string): Paginated {
  const pageSize = queryInt(query, "page_size", 20);
  return { data: [], meta: { total: 0, page: 1, page_size: pageSize, total_pages: 1 } };
}

// Endpoints que el backend real tampoco sirve (404 logueado) o no aplican a un
// rubro: su vacío es esperado, no un hueco de fixture.
const KNOWN_EMPTY =
  /^\/(tenant-economics|calendar-events|quotes|subentidades|repartidores|delivery\/|leads\/[^/]+\/(interactions|stage-history)|mesas\/disponibilidad|reservaciones\/disponibilidad|sucursales\/[^/]+\/whatsapp|qr\/)/;

const warned = new Set<string>();
/** Señal SOLO en dev para QA de Fase 2: un path sin snapshot ni builder. */
function warnMissing(clean: string): void {
  if (process.env.NODE_ENV === "production") return;
  if (KNOWN_EMPTY.test(clean) || warned.has(clean)) return;
  warned.add(clean);
  console.warn(`[demo] sin snapshot para GET ${clean} → sirvo vacío (revisar Fase 1)`);
}

/** Builders sintéticos rubro-aware para paths sin snapshot (o de respaldo). */
function synthetic(clean: string, query: string, key: RubroKey): unknown {
  switch (clean) {
    case "/tenants/me":
      return buildTenant(key);
    case "/auth/me":
      return buildUser();
    case "/metricas/dashboard":
      return buildDashboardKpis(key);
    case "/metricas/revenue":
      return buildRevenue(key);
    case "/metricas/operativo":
      return buildOperational(key);
    case "/metricas/productos-top":
      return buildTopProducts(key, queryInt(query, "limit", 5));
    case "/metricas/financiero":
      return buildFinancial(key);
    case "/metricas/weekly-activity":
      return buildWeeklyActivity(key);
    case "/metricas/menu-engineering":
      return buildMenuEngineering(key);
    case "/ai-conversations":
      return buildConversations(key, queryInt(query, "page_size", 20));
    case "/pendientes":
      return buildRevisiones(key, queryInt(query, "page_size", 20));
    case "/alertas":
      return buildAlerts(key, queryInt(query, "page_size", 20));
    // Endpoints que el backend real 404ea (tenant-economics, calendar-events,
    // quotes, leads/{id}/interactions, …): sobre vacío → EmptyState, fiel al
    // comportamiento logueado. `/…/latest` y objetos singulares → null.
    default:
      warnMissing(clean);
      return clean.endsWith("/latest") ? null : emptyPage(query);
  }
}

// ── Entrada pública ────────────────────────────────────────────────────────
/** Resuelve el fixture para un GET dado el rubro activo. Determinista. */
export function demoResolve<T>(path: string, rubro: RubroKey): Promise<T> {
  try {
    const [rawClean, query = ""] = path.split("?");
    const clean = rawClean ?? path;

    // La identidad del tenant siempre es rubro-propia (branding correcto en la
    // cabecera), incluso para el héroe usamos el snapshot real vía snapshot-match.
    if (clean === "/tenants/me" && rubro !== HERO) {
      return Promise.resolve(buildTenant(rubro) as T);
    }

    const snap = matchSnapshot(clean);
    if (snap) {
      const sliced = reslice(snap.data, query);
      const out = rubro === HERO ? sliced : deepReskin(sliced, moneyScale(rubro));
      return Promise.resolve(out as T);
    }

    return Promise.resolve(synthetic(clean, query, rubro) as T);
  } catch (err) {
    return Promise.reject(err instanceof Error ? err : new Error(String(err)));
  }
}
