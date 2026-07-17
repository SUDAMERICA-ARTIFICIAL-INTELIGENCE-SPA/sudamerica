// ── Generador del registro de rutas del showroom ──────────────────────────
// Escanea `frontend/app/(dashboard)/**/page.tsx` y emite un mapa
// `ruta → dynamic(() => import(page))` que el catch-all del showroom usa para
// renderizar la página real de (dashboard) correspondiente dentro del shell demo.
// Regenerar tras añadir/quitar páginas: `node tools/gen_showroom_routes.mjs`.

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FE = resolve(__dirname, "../frontend");
const DASH = resolve(FE, "app/(dashboard)");
const OUT = resolve(FE, "lib/demo/showroom-routes.generated.tsx");
// Lista plana de claves, SIN "use client": la consume `generateStaticParams`
// (server) del catch-all del showroom para pre-renderizar el árbol del héroe.
// El registro `.generated.tsx` es un módulo cliente → sus claves no son legibles
// desde un server component (llegan como client-refs).
const OUT_KEYS = resolve(FE, "lib/demo/showroom-routes.keys.ts");

/**
 * ¿La página es un stub legacy de puro `redirect()` (sin JSX propio)? Esas rutas
 * planas existen solo para no romper deep-links viejos y saltan a su ruta canónica
 * con una ruta ABSOLUTA (sin el prefijo `/showroom/<rubro>`). En la vitrina eso
 * navegaría FUERA del showroom → se excluyen del registro (su destino canónico ya
 * está mapeado). Heurística: llama `redirect(` y no renderiza JSX (`return (`/`<`).
 */
function isRedirectStub(file) {
  const src = readFileSync(file, "utf8");
  return /\bredirect\s*\(/.test(src) && !/return\s*[(<]/.test(src);
}

/** Recorre el árbol y devuelve rutas relativas a (dashboard) con page.tsx real. */
function walk(dir, base = "") {
  const routes = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      // Ignora segmentos dinámicos y grupos de ruta (no aplican al showroom).
      if (entry.name.startsWith("[") || entry.name.startsWith("(")) continue;
      routes.push(...walk(resolve(dir, entry.name), base ? `${base}/${entry.name}` : entry.name));
    } else if (entry.name === "page.tsx" && base && !isRedirectStub(resolve(dir, entry.name))) {
      routes.push(base);
    }
  }
  return routes;
}

const routes = walk(DASH).sort();

// Ident por índice: evita colisiones (p.ej. `documentos-tributarios` vs
// `documentos/tributarios` normalizarían al mismo nombre).
const ident = (_r, i) => `P${i}`;
const lines = [
  "// GENERADO por tools/gen_showroom_routes.mjs — NO editar a mano.",
  "// Mapa ruta → página real de (dashboard), cargada dinámicamente en el shell demo.",
  '"use client";',
  "",
  'import dynamic from "next/dynamic";',
  'import type { ComponentType } from "react";',
  "",
  // Cast del default a ComponentType: algunas páginas legacy de redirect tienen
  // default `() => void`, que `dynamic` rechaza (no son alcanzables por el nav).
  ...routes.map(
    (r, i) =>
      `const ${ident(r, i)} = dynamic(() => import("@/app/(dashboard)/${r}/page").then((m) => ({ default: m.default as ComponentType })));`,
  ),
  "",
  "/** Ruta relativa (sin `/` inicial) → componente de página. */",
  "export const SHOWROOM_ROUTES: Record<string, ComponentType> = {",
  ...routes.map((r, i) => `  ${JSON.stringify(r)}: ${ident(r, i)},`),
  "};",
  "",
  "/** Ruta por defecto del showroom (landing de un rubro) = el dashboard/resumen. */",
  'export const SHOWROOM_DEFAULT_ROUTE = "dashboard";',
  "",
];

writeFileSync(OUT, lines.join("\n"), "utf8");

const keyLines = [
  "// GENERADO por tools/gen_showroom_routes.mjs — NO editar a mano.",
  "// Claves de ruta del showroom (server-safe, sin \"use client\"): las usa",
  "// generateStaticParams del catch-all para pre-renderizar el árbol del héroe.",
  "export const SHOWROOM_ROUTE_KEYS: readonly string[] = [",
  ...routes.map((r) => `  ${JSON.stringify(r)},`),
  "];",
  "",
];
writeFileSync(OUT_KEYS, keyLines.join("\n"), "utf8");
console.log(`✓ ${OUT} (${routes.length} rutas)`);
console.log(`✓ ${OUT_KEYS} (${routes.length} claves)`);
