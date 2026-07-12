// Test anti-drift seed↔fixture (Fase B, Paso 5) — red de seguridad de la cadena única de verdad.
//
// La tabla BD `rubros` (migración 028) se seedea con `backend/infra/029_rubros_seed.sql`, generado
// por `tools/gen_rubros_seed.mjs` desde el fixture `./__fixtures__/rubros.manifest.json` (la
// verdad-py del Paso 4). Este test REGENERA el SQL en memoria desde el mismo fixture (con el mismo
// builder que usa el CLI) y lo compara byte a byte con el archivo commiteado. Cualquier drift
// —fixture editado sin regenerar el seed, o el .sql editado a mano— FALLA.
//
// Regenerar el seed cuando cambie el fixture (que a su vez deriva de diccionario.py):
//   node tools/gen_rubros_seed.mjs

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildSeedSql } from "../../tools/rubros-seed.mjs";
import manifest from "./__fixtures__/rubros.manifest.json";

// Vitest corre con cwd = frontend/ (donde vive vitest.config.ts); el seed está un nivel arriba.
const SEED_SQL_PATH = resolve(
  process.cwd(),
  "..",
  "backend",
  "infra",
  "029_rubros_seed.sql",
);

describe("sync seed↔fixture del manifiesto de rubros", () => {
  const committed = readFileSync(SEED_SQL_PATH, "utf8");
  const regenerated = buildSeedSql(manifest);

  it("el 029_rubros_seed.sql commiteado coincide byte a byte con el regenerado del fixture", () => {
    expect(committed).toBe(regenerated);
  });

  it("el seed cubre exactamente los rubros del fixture (101+)", () => {
    const keys = Object.keys(manifest.rubros);
    for (const key of keys) {
      expect(committed).toContain(`('${key}', `);
    }
    expect(keys.length).toBeGreaterThanOrEqual(101);
  });

  it("restaurante se seedea byte-idéntico a la verdad-py (oráculo de no-regresión)", () => {
    const r = manifest.rubros.restaurante as { labels: Record<string, string> };
    // Los labels curados de restaurante (p.ej. "Carta", "Comanda") viajan verbatim al seed.
    const labelsJson = JSON.stringify(r.labels);
    expect(committed).toContain(labelsJson);
    expect(committed).toContain("'restaurante', 'Restaurante'");
  });

  it("inicializa el contador global de versión del manifiesto en platform_config", () => {
    expect(committed).toContain("'rubro_manifest_version'");
    expect(committed).toContain("ON CONFLICT (key) DO NOTHING");
  });
});
