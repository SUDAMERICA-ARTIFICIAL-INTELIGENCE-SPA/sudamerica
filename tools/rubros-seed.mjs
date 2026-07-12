// Generador puro del seed SQL de la tabla `rubros` (Fase B, Paso 5).
//
// Fuente: el manifiesto canónico `frontend/lib/__fixtures__/rubros.manifest.json` (la verdad-py
// commiteada, emitida por `backend/shared/rubros/export_manifest.py` y guardada por
// `frontend/lib/rubros.parity.test.ts`). Este módulo NO lee del disco: recibe el manifiesto ya
// parseado y devuelve el texto SQL determinista, de modo que tanto el CLI
// (`tools/gen_rubros_seed.mjs`) como el test anti-drift (`frontend/lib/rubros.seed.test.ts`)
// produzcan EXACTAMENTE el mismo SQL. Cadena única de verdad: diccionario.py ⇒ fixture ⇒ seed.
//
// Node (no python) para esquivar el "no-python en host" y garantizar seed == verdad-py.

/** Columnas del INSERT, en orden fijo (espejo de RubroManifest + version). */
const COLUMNS = [
  "key",
  "nombre",
  "emoji",
  "sector",
  "labels",
  "capacidades",
  "sub_entidad_label",
  "recurso",
  "variantes",
  "precio_medida",
  "categorias_semilla",
  "version",
];

/** Literal SQL de texto: comilla simple, con escape de comillas internas. */
function sqlStr(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

/** Literal SQL jsonb determinista (JSON compacto, preservando el orden del fixture). */
function sqlJsonb(value) {
  return `${sqlStr(JSON.stringify(value))}::jsonb`;
}

/** Fila VALUES de un rubro (orden de COLUMNS). */
function rowValues(r) {
  return [
    sqlStr(r.key),
    sqlStr(r.nombre),
    sqlStr(r.emoji),
    sqlStr(r.sector),
    sqlJsonb(r.labels),
    sqlJsonb(r.capacidades),
    r.sub_entidad_label == null ? "NULL" : sqlStr(r.sub_entidad_label),
    r.recurso ? "true" : "false",
    r.variantes ? "true" : "false",
    r.precio_medida ? "true" : "false",
    sqlJsonb(r.categorias_semilla ?? []),
    "1",
  ].join(", ");
}

/**
 * Construye el SQL del seed (migración 029) a partir del manifiesto parseado.
 * Determinista: rubros en orden alfabético por clave; UPSERT idempotente.
 */
export function buildSeedSql(manifest) {
  const keys = Object.keys(manifest.rubros).sort();
  const rows = keys.map((k) => `  (${rowValues(manifest.rubros[k])})`).join(",\n");

  const header = [
    "-- 029_rubros_seed.sql",
    "-- GENERADO por tools/gen_rubros_seed.mjs desde frontend/lib/__fixtures__/rubros.manifest.json.",
    "-- NO editar a mano: `frontend/lib/rubros.seed.test.ts` falla ante cualquier drift.",
    "-- Fase B (Paso 5). Seed reproducible del manifiesto de rubro: cadena unica de verdad",
    "-- diccionario.py => fixture => seed. UPSERT idempotente (ON CONFLICT).",
    "",
  ].join("\n");

  const insert = [
    `INSERT INTO rubros (${COLUMNS.join(", ")})`,
    "VALUES",
    `${rows}`,
    "ON CONFLICT (key) DO UPDATE SET",
    "  nombre = EXCLUDED.nombre,",
    "  emoji = EXCLUDED.emoji,",
    "  sector = EXCLUDED.sector,",
    "  labels = EXCLUDED.labels,",
    "  capacidades = EXCLUDED.capacidades,",
    "  sub_entidad_label = EXCLUDED.sub_entidad_label,",
    "  recurso = EXCLUDED.recurso,",
    "  variantes = EXCLUDED.variantes,",
    "  precio_medida = EXCLUDED.precio_medida,",
    "  categorias_semilla = EXCLUDED.categorias_semilla,",
    "  updated_at = NOW();",
    "",
  ].join("\n");

  // Inicializa el contador global de version del manifiesto (default: fila en platform_config).
  // DO NOTHING: re-seedear NO resetea la version si un admin ya la bumpeo en runtime.
  const versionInit = [
    "-- Contador global de version del manifiesto (Fase B). DO NOTHING preserva bumps de runtime.",
    "INSERT INTO platform_config (key, value)",
    "VALUES ('rubro_manifest_version', '{\"version\": 1}'::jsonb)",
    "ON CONFLICT (key) DO NOTHING;",
    "",
  ].join("\n");

  return `${header}\n${insert}\n${versionInit}`;
}
