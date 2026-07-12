// Test de paridad py↔ts (Fase A, Paso 4) — red de seguridad del doble SSOT del rubro.
//
// La fuente de verdad es el backend `shared/rubros/diccionario.py`. El exporter
// `backend/shared/rubros/export_manifest.py` emite el manifiesto canónico a
// `./__fixtures__/rubros.manifest.json` (commiteado). Este test RECONSTRUYE el mismo
// manifiesto desde el espejo ts (`RUBROS`, `PRIMITIVAS`, `CAPACIDADES`, `RUBRO_DEFAULT`)
// y afirma igualdad campo a campo. Si `rubros.ts` diverge de la fuente py en cualquier
// campo contractual (claves de rubro, 12 labels, capacidades, sector, sub-entidad, flags,
// categorías semilla) el test FALLA.
//
// Regenerar el fixture cuando cambie el py:
//   python backend/shared/rubros/export_manifest.py > frontend/lib/__fixtures__/rubros.manifest.json

import { describe, expect, it } from "vitest";
import manifest from "./__fixtures__/rubros.manifest.json";
import { CAPACIDADES } from "./capacidades";
import { PRIMITIVAS, RUBROS, RUBRO_DEFAULT, type RubroKey, getRubroDef } from "./rubros";

interface RubroEntry {
  key: string;
  nombre: string;
  emoji: string;
  sector: string;
  labels: Record<string, string>;
  capacidades: string[];
  sub_entidad_label: string | null;
  recurso: boolean;
  variantes: boolean;
  precio_medida: boolean;
  categorias_semilla: string[];
}

/** Proyección contractual de un rubro del espejo ts al shape canónico del manifiesto py. */
function tsEntry(key: string): RubroEntry {
  const def = getRubroDef(key);
  const labels: Record<string, string> = {};
  for (const p of PRIMITIVAS) {
    labels[p] = def.labels[p];
  }
  return {
    key: def.key,
    nombre: def.nombre,
    emoji: def.emoji,
    sector: def.sector,
    labels,
    capacidades: [...def.capacidades],
    sub_entidad_label: def.subEntidadLabel ?? null,
    recurso: def.recurso ?? false,
    variantes: def.variantes ?? true,
    precio_medida: def.precioMedida ?? false,
    categorias_semilla: [...def.categoriasSemilla],
  };
}

describe("paridad py↔ts del manifiesto de rubros", () => {
  it("el fixture py declara el mismo contrato de nivel superior que el ts", () => {
    expect(manifest.rubro_default).toBe(RUBRO_DEFAULT);
    expect(manifest.primitivas).toEqual([...PRIMITIVAS]);
    expect(manifest.capacidades).toEqual([...CAPACIDADES]);
  });

  it("el conjunto de claves de rubro es idéntico en py y ts", () => {
    const tsKeys = Object.keys(RUBROS).sort();
    const pyKeys = Object.keys(manifest.rubros).sort();
    expect(tsKeys).toEqual(pyKeys);
  });

  const pyRubros = manifest.rubros as Record<string, RubroEntry>;
  for (const key of Object.keys(pyRubros).sort()) {
    it(`rubro "${key}" coincide byte a byte entre py y ts`, () => {
      expect(tsEntry(key)).toEqual(pyRubros[key]);
    });
  }

  it("ningún rubro ts queda fuera de la comparación (cobertura completa)", () => {
    const tsKeys = Object.keys(RUBROS) as RubroKey[];
    expect(tsKeys.length).toBe(Object.keys(pyRubros).length);
    expect(tsKeys.length).toBeGreaterThanOrEqual(101);
  });
});
