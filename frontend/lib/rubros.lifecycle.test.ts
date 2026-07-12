// Test del ciclo de vida seed/runtime del roster (Fase C, Paso 6) — invariantes de la migración
// 030 y del acotamiento del sync seed↔fixture a `origen='seed'`.
//
// La Fase C introduce dos clases de rubro: `seed` (proyección de diccionario.py, membresía
// inmutable, byte-idéntica, test-guarded) y `runtime` (creado por admin vía POST, vive SOLO en
// BD, EXENTO de la cadena una-sola-verdad). Este test verifica por LECTURA que:
//   1. la migración 030 añade `origen`/`activo` con los defaults correctos y NO toca el seed 029;
//   2. el seed 029 no materializa `origen`/`activo` (llegan por DEFAULT ⇒ backfill 'seed'/true);
//   3. el sync seed↔fixture (rubros.seed.test.ts) cubre SOLO el roster de código: por
//      construcción compara el .sql 029 (solo filas seed) con el fixture; un rubro runtime
//      —que nunca entra al fixture ni al 029— no puede romperlo.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import manifest from "./__fixtures__/rubros.manifest.json";

const INFRA = resolve(process.cwd(), "..", "backend", "infra");
const MIG_030 = readFileSync(resolve(INFRA, "030_rubros_lifecycle.sql"), "utf8");
const SEED_029 = readFileSync(resolve(INFRA, "029_rubros_seed.sql"), "utf8");

describe("migración 030 — clase de rubro + ciclo de vida", () => {
  it("añade la columna `origen` (seed|runtime) con DEFAULT 'seed' y CHECK", () => {
    expect(MIG_030).toMatch(/ADD COLUMN IF NOT EXISTS origen/);
    expect(MIG_030).toMatch(/DEFAULT 'seed'/);
    expect(MIG_030).toMatch(/CHECK \(origen IN \('seed', 'runtime'\)\)/);
  });

  it("añade la columna `activo` con DEFAULT TRUE", () => {
    expect(MIG_030).toMatch(/ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE/);
  });

  it("NO toca el contenido del seed: no contiene INSERT/UPDATE de datos de rubros", () => {
    expect(MIG_030).not.toMatch(/INSERT INTO rubros/i);
    expect(MIG_030).not.toMatch(/UPDATE rubros SET/i);
  });

  it("`rubros` sigue global: la migración no le añade RLS/tenant_isolation", () => {
    expect(MIG_030).not.toMatch(/tenant_isolation/i);
    expect(MIG_030).not.toMatch(/ENABLE ROW LEVEL SECURITY/i);
  });
});

describe("acotamiento del sync seed↔fixture a origen='seed'", () => {
  it("el seed 029 no materializa `origen`/`activo` (llegan por DEFAULT ⇒ backfill seed/activo)", () => {
    // El backfill es implícito por los DEFAULT de 030; 029 no menciona esas columnas.
    expect(SEED_029).not.toMatch(/\borigen\b/);
    expect(SEED_029).not.toMatch(/\bactivo\b/);
  });

  it("todas las keys del fixture (roster de código) están en el seed; el fixture es solo-seed", () => {
    const keys = Object.keys(manifest.rubros);
    for (const key of keys) {
      expect(SEED_029).toContain(`('${key}', `);
    }
  });

  it("una key de rubro runtime hipotética NO está en el fixture ni en el seed (no rompe el sync)", () => {
    const runtimeKey = "rubro_runtime_inexistente";
    expect(Object.keys(manifest.rubros)).not.toContain(runtimeKey);
    expect(SEED_029).not.toContain(`('${runtimeKey}', `);
  });
});
