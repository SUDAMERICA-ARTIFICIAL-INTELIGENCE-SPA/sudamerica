// ── Snapshot de fixtures demo desde el backend seedeado ────────────────────
// Fuente de verdad de la VITRINA para el rubro `cosmetica_belleza` (aura-demo):
// con el stack real levantado y seedeado (OLA A + OLA B), loguea como demo@aura.cl
// y hace GET a cada endpoint que consumen las 49 subs, guardando la respuesta
// como JSON estático en `frontend/lib/demo/snapshots/cosmetica_belleza/<slug>.json`.
//
// Determinista: mismo seed ⇒ mismos bytes. Las fechas ISO vienen del seed
// (ancladas al día del snapshot). Re-seedear ⇒ re-generar (`node tools/snapshot_demo_fixtures.mjs`).
//
// Uso:
//   node tools/snapshot_demo_fixtures.mjs
// Env (con defaults del stack portable local):
//   API_BASE   (default http://127.0.0.1:8000/api/v1/core)
//   DEMO_EMAIL (default demo@aura.cl)
//   DEMO_PASS  (default Demo1234)

import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, "..");
const OUT_DIR = resolve(REPO, "frontend/lib/demo/snapshots/cosmetica_belleza");

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8000/api/v1/core";
const DEMO_EMAIL = process.env.DEMO_EMAIL ?? "demo@aura.cl";
const DEMO_PASS = process.env.DEMO_PASS ?? "Demo1234";

// page_size amplio para capturar "todo": el resolver re-pagina en runtime según
// lo que pida cada hook. El backend topa page_size en 100 (Field le=100).
const BIG = 100;

/**
 * Endpoints a capturar. `slug` = nombre de archivo. `query` = querystring exacto.
 * `serve` = ruta RELATIVA con la que el frontend pide el dato (la que empareja el
 * resolver); por defecto = `path`. Difieren cuando el hook usa un `service` cuya
 * base ya incluye un prefijo (p.ej. `dialer` = `/api/v1/core/ai`, así que el hook
 * pide `/config` aunque el backend lo sirva en `/ai/config`).
 * `detail` = { list, param } resuelve un {id} tomándolo del primer item de una
 * captura de lista previa (vistas de detalle). El orden importa: listas antes que
 * sus detalles. `serve` con `{id}` lo empareja el resolver id-agnósticamente.
 */
const SPECS = [
  // Auth / tenant
  { slug: "auth-me", path: "/auth/me" },
  { slug: "tenants-me", path: "/tenants/me" },
  { slug: "rubros-disponibles", path: "/rubros/disponibles" },

  // Métricas (objetos y series)
  { slug: "metricas-dashboard", path: "/metricas/dashboard" },
  { slug: "metricas-revenue", path: "/metricas/revenue" },
  { slug: "metricas-operativo", path: "/metricas/operativo" },
  { slug: "metricas-financiero", path: "/metricas/financiero" },
  { slug: "metricas-productos-top", path: "/metricas/productos-top", query: "limit=10" },
  { slug: "metricas-weekly-activity", path: "/metricas/weekly-activity" },
  { slug: "metricas-menu-engineering", path: "/metricas/menu-engineering" },
  { slug: "metricas-conversion", path: "/metricas/conversion" },
  { slug: "metricas-leads-estado", path: "/metricas/leads-estado" },
  { slug: "metricas-por-sector", path: "/metricas/por-sector" },
  { slug: "metricas-actividad", path: "/metricas/actividad" },
  { slug: "metricas-cobros", path: "/metricas/cobros" },
  { slug: "metricas-tesoreria", path: "/metricas/tesoreria" },
  { slug: "metricas-flujo-caja", path: "/metricas/flujo-caja" },
  { slug: "metricas-por-canal", path: "/metricas/por-canal" },
  { slug: "metricas-segmentacion-clientes", path: "/metricas/segmentacion-clientes" },
  { slug: "metricas-loyalty-insights", path: "/metricas/loyalty-insights" },

  // Catálogo
  { slug: "categorias", path: "/categorias" },
  { slug: "productos", path: "/productos", query: `page=1&page_size=${BIG}` },
  { slug: "subentidades", path: "/subentidades" },
  { slug: "modifier-groups", path: "/modifier-groups" },
  { slug: "suministros", path: "/suministros" },
  { slug: "suministros-recetas", path: "/suministros/recetas" },

  // Ventas / pedidos
  { slug: "ventas", path: "/ventas", query: `page=1&page_size=${BIG}` },
  { slug: "comandas", path: "/comandas", query: `page=1&page_size=${BIG}` },
  { slug: "comandas-kds", path: "/comandas/kds" },
  { slug: "mesas", path: "/mesas" },
  { slug: "mesas-disponibilidad", path: "/mesas/disponibilidad" },
  { slug: "reservaciones", path: "/reservaciones", query: `page=1&page_size=${BIG}` },
  { slug: "reservaciones-disponibilidad", path: "/reservaciones/disponibilidad" },
  { slug: "delivery-pending", path: "/delivery/pending" },
  { slug: "repartidores", path: "/repartidores" },
  { slug: "sales-targets", path: "/sales-targets" },

  // Compras (OLA B)
  { slug: "compras-resumen", path: "/compras/resumen" },
  { slug: "compras-ordenes", path: "/compras/ordenes", query: `page=1&page_size=${BIG}` },
  { slug: "compras-facturas", path: "/compras/facturas", query: `page=1&page_size=${BIG}` },
  { slug: "compras-proveedores", path: "/compras/proveedores", query: `page=1&page_size=${BIG}` },
  { slug: "compras-recepciones", path: "/compras/recepciones", query: `page=1&page_size=${BIG}` },
  { slug: "compras-requisiciones", path: "/compras/requisiciones", query: `page=1&page_size=${BIG}` },
  { slug: "compras-cotizaciones", path: "/compras/cotizaciones", query: `page=1&page_size=${BIG}` },
  { slug: "compras-evaluacion", path: "/compras/evaluacion" },

  // Inventario (OLA B)
  { slug: "inventario-movimientos", path: "/inventario/movimientos", query: `page=1&page_size=${BIG}` },

  // Contactos / CRM
  { slug: "leads", path: "/leads", query: `page=1&page_size=${BIG}` },
  { slug: "campanas", path: "/campanas" },
  { slug: "devoluciones", path: "/devoluciones", query: `page=1&page_size=${BIG}` },

  // Conversaciones / IA (los `serve` con dialer-base se piden sin el prefijo /ai)
  { slug: "ai-conversations", path: "/ai-conversations", query: `page=1&page_size=${BIG}` },
  { slug: "ai-config", path: "/ai/config", serve: "/config" },
  {
    slug: "ai-conversations-list",
    path: "/ai/conversations",
    serve: "/conversations",
    query: `page=1&page_size=${BIG}`,
  },
  { slug: "ai-knowledge", path: "/ai/knowledge", serve: "/knowledge" },
  { slug: "alertas", path: "/alertas", query: `page=1&page_size=${BIG}` },
  { slug: "plantillas", path: "/plantillas" },
  { slug: "pendientes", path: "/pendientes", query: `page=1&page_size=${BIG}` },

  // ROI / economics
  { slug: "tenant-economics", path: "/tenant-economics", query: `page=1&page_size=${BIG}` },
  { slug: "tenant-economics-latest", path: "/tenant-economics/latest" },

  // Agenda
  { slug: "calendar-events", path: "/calendar-events" },

  // Documentos
  { slug: "documentos", path: "/documentos", query: `page=1&page_size=${BIG}` },

  // Equipo / config / billing
  { slug: "usuarios", path: "/usuarios" },
  { slug: "sucursales", path: "/sucursales" },
  { slug: "sucursales-whatsapp-groups", path: "/sucursales/whatsapp-groups" },
  { slug: "billing-usage", path: "/billing/usage" },
  { slug: "menu-import-history", path: "/menu/import/history" },
  { slug: "sudamerica-history", path: "/sudamerica/history" },

  // Detalles (resueltos del primer item de su lista; el resolver empareja el {id}
  // id-agnósticamente, así que cualquier fila abierta en la vitrina muestra este dato).
  {
    slug: "leads-detail",
    path: "/leads/{id}",
    serve: "/leads/{id}",
    detail: { list: "leads", param: "id" },
  },
  {
    slug: "leads-interactions",
    path: "/leads/{id}/interactions",
    serve: "/leads/{id}/interactions",
    query: "page_size=50",
    detail: { list: "leads", param: "id" },
  },
  {
    slug: "leads-stage-history",
    path: "/leads/{id}/stage-history",
    serve: "/leads/{id}/stage-history",
    query: "page_size=20",
    detail: { list: "leads", param: "id" },
  },
  {
    slug: "quotes",
    path: "/quotes",
    serve: "/quotes",
    query: "page_size=20",
    detail: { list: "leads", param: "lead_id_query" },
  },
  {
    slug: "productos-detail",
    path: "/productos/{id}",
    serve: "/productos/{id}",
    detail: { list: "productos", param: "id" },
  },
  {
    slug: "ventas-detail",
    path: "/ventas/{id}",
    serve: "/ventas/{id}",
    detail: { list: "ventas", param: "id" },
  },
  {
    slug: "compras-ordenes-detail",
    path: "/compras/ordenes/{id}",
    serve: "/compras/ordenes/{id}",
    detail: { list: "compras-ordenes", param: "id" },
  },
];

async function login() {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: DEMO_EMAIL, password: DEMO_PASS }),
  });
  if (!res.ok) throw new Error(`login ${res.status}: ${await res.text()}`);
  const json = await res.json();
  if (!json.access_token) throw new Error("login: sin access_token");
  return json.access_token;
}

async function getRaw(token, path, query) {
  const url = `${API_BASE}${path}${query ? `?${query}` : ""}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

/**
 * GET con auto-paginación: si la respuesta es un sobre `{data, meta}` con más de
 * una página, recorre todas y concatena `data`, dejando `meta` reflejando el set
 * COMPLETO (page=1, page_size=total, total_pages=1). Así el snapshot es fiel al
 * total real del dashboard logueado y el resolver re-pagina en runtime.
 */
async function get(token, path, query) {
  const first = await getRaw(token, path, query);
  const meta = first?.meta;
  if (!meta || !Array.isArray(first?.data) || (meta.total_pages ?? 1) <= 1) {
    return first;
  }
  const params = new URLSearchParams(query ?? "");
  const rows = [...first.data];
  for (let page = 2; page <= meta.total_pages; page++) {
    params.set("page", String(page));
    const next = await getRaw(token, path, params.toString());
    if (Array.isArray(next?.data)) rows.push(...next.data);
  }
  return {
    ...first,
    data: rows,
    meta: { total: rows.length, page: 1, page_size: rows.length, total_pages: 1 },
  };
}

/** Primer id "razonable" de una respuesta de lista (soporta {data:[]} o []). */
function firstId(captured) {
  const arr = Array.isArray(captured) ? captured : (captured?.data ?? captured?.items ?? []);
  const first = Array.isArray(arr) ? arr[0] : undefined;
  return first?.id ?? first?.lead_id ?? first?.producto_id ?? first?.venta_id ?? null;
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const token = await login();
  console.log(`✓ login ${DEMO_EMAIL}`);

  const captured = new Map();
  const manifest = [];
  let ok = 0;
  let skipped = 0;

  for (const spec of SPECS) {
    let path = spec.path;
    let query = spec.query;

    if (spec.detail) {
      const src = captured.get(spec.detail.list);
      if (!src) {
        console.warn(`… skip ${spec.slug}: lista '${spec.detail.list}' no capturada`);
        skipped++;
        continue;
      }
      const id = firstId(src);
      if (!id) {
        console.warn(`… skip ${spec.slug}: lista '${spec.detail.list}' sin items`);
        skipped++;
        continue;
      }
      if (spec.detail.param === "lead_id_query") {
        const qp = new URLSearchParams(query ?? "");
        qp.set("lead_id", id);
        query = qp.toString();
      } else {
        path = spec.path.replace("{id}", encodeURIComponent(id));
      }
    }

    try {
      const data = await get(token, path, query);
      captured.set(spec.slug, data);
      await writeFile(
        resolve(OUT_DIR, `${spec.slug}.json`),
        `${JSON.stringify(data, null, 2)}\n`,
        "utf8",
      );
      // `serve` = clave RELATIVA que empareja el resolver (default = path base,
      // sin resolver ids: las detalle conservan `{id}` para match id-agnóstico).
      manifest.push({ slug: spec.slug, serve: spec.serve ?? spec.path, query: query ?? null });
      ok++;
      console.log(`✓ ${spec.slug}  ←  ${path}${query ? `?${query}` : ""}`);
    } catch (err) {
      console.error(`✗ ${spec.slug}: ${err.message}`);
      skipped++;
    }
  }

  await writeFile(
    resolve(OUT_DIR, "index.json"),
    `${JSON.stringify({ rubro: "cosmetica_belleza", generatedFrom: API_BASE, entries: manifest }, null, 2)}\n`,
    "utf8",
  );

  // Barrel TS con imports estáticos → el resolver carga los snapshots sin 59
  // imports a mano y Next los empaqueta (code-split dentro del bundle showroom).
  const ident = (slug) => `s_${slug.replace(/[^a-zA-Z0-9]/g, "_")}`;
  const barrel = [
    "// GENERADO por tools/snapshot_demo_fixtures.mjs — NO editar a mano.",
    "// Snapshots reales del rubro cosmetica_belleza (aura-demo) capturados del backend seedeado.",
    'import type { SnapshotEntry } from "@/lib/demo/snapshot-types";',
    ...manifest.map((m) => `import ${ident(m.slug)} from "./${m.slug}.json";`),
    "",
    "export const COSMETICA_SNAPSHOTS: readonly SnapshotEntry[] = [",
    ...manifest.map(
      (m) =>
        `  { serve: ${JSON.stringify(m.serve)}, query: ${JSON.stringify(m.query)}, data: ${ident(m.slug)} as unknown },`,
    ),
    "];",
    "",
  ].join("\n");
  await writeFile(resolve(OUT_DIR, "store.generated.ts"), barrel, "utf8");

  console.log(`\n${ok} capturados, ${skipped} omitidos → ${OUT_DIR}`);
  console.log(`✓ barrel store.generated.ts (${manifest.length} entries)`);
  if (ok === 0) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
