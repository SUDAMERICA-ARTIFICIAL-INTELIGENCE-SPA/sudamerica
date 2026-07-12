// Test del descubrimiento del set vivo de rubros (Fase C, Paso 6).
//
// Cubre la fusión pura `mergeRubroOptions` (baseline de código ∪ set vivo de la API), que permite
// ofrecer rubros `origen='runtime'` en la UI sin degradar el fixture como baseline. NO toca red.

import { describe, expect, it } from "vitest";
import { RUBRO_OPTIONS } from "./rubros";
import { type RubroDisponible, mergeRubroOptions } from "./rubros-live";

function liveRubro(over: Partial<RubroDisponible> & { key: string }): RubroDisponible {
  return {
    key: over.key,
    nombre: over.nombre ?? over.key,
    emoji: over.emoji ?? "🆕",
    sector: over.sector ?? "otro",
    labels: over.labels ?? {},
    capacidades: over.capacidades ?? ["catalogo"],
    sub_entidad_label: over.sub_entidad_label ?? null,
    recurso: over.recurso ?? false,
    variantes: over.variantes ?? true,
    precio_medida: over.precio_medida ?? false,
    categorias_semilla: over.categorias_semilla ?? [],
  };
}

describe("mergeRubroOptions — set vivo sobre baseline de código", () => {
  it("con set vivo vacío (API caída) conserva el baseline estático intacto (fail-open)", () => {
    const merged = mergeRubroOptions([]);
    expect(merged).toEqual(RUBRO_OPTIONS.map((o) => ({ ...o })));
  });

  it("anexa un rubro runtime nuevo (ausente del fixture) al final, preservando el orden", () => {
    const merged = mergeRubroOptions([
      liveRubro({ key: "carro_arriendo", nombre: "Arriendo de Carros", emoji: "🚙" }),
    ]);
    expect(merged.length).toBe(RUBRO_OPTIONS.length + 1);
    expect(merged[merged.length - 1]).toEqual({
      value: "carro_arriendo",
      label: "Arriendo de Carros",
      emoji: "🚙",
    });
    // El baseline no se reordena.
    expect(merged.slice(0, RUBRO_OPTIONS.length).map((o) => o.value)).toEqual(
      RUBRO_OPTIONS.map((o) => o.value),
    );
  });

  it("un rubro seed presente en el set vivo NO se duplica (upsert por key)", () => {
    const merged = mergeRubroOptions([
      liveRubro({ key: "restaurante", nombre: "Restaurante", emoji: "🍽️" }),
    ]);
    const restaurantes = merged.filter((o) => o.value === "restaurante");
    expect(restaurantes.length).toBe(1);
    expect(merged.length).toBe(RUBRO_OPTIONS.length);
  });
});
