// Contract tests del catálogo de capacidades (espejo de shared/tests/test_capacidades.py).
// Auto-escalan desde el SSOT (100/100 con `capacidades` requerido). Guardrail crítico:
// restaurante == [catalogo, agenda, pedidos, pagos, delivery, mesas] (byte-identidad).
import { describe, expect, it } from "vitest";
import { CAPACIDADES, CAPACIDADES_META, type Capacidad } from "./capacidades";
import { RUBROS, type RubroKey } from "./rubros";

const RUBRO_KEYS: RubroKey[] = Object.keys(RUBROS) as RubroKey[];

const RESTAURANTE_CAPACIDADES: readonly Capacidad[] = [
  "catalogo",
  "agenda",
  "pedidos",
  "pagos",
  "delivery",
  "mesas",
];

describe("catálogo de capacidades", () => {
  it("son 22 únicas en CAP_ORDER (idéntico al backend)", () => {
    expect([...CAPACIDADES]).toEqual([
      "catalogo",
      "agenda",
      "cotizador",
      "pedidos",
      "pagos",
      "delivery",
      "suscripciones",
      "soporte",
      "proyectos",
      "inventario",
      "compras",
      "produccion",
      "expedientes",
      "contratos",
      "cursos",
      "arriendos",
      "facturacion",
      "fidelizacion",
      "campanas",
      "terreno",
      "mesas",
      "consentimientos",
    ]);
    expect(new Set(CAPACIDADES).size).toBe(22);
  });

  it("la metadata cubre todo el catálogo", () => {
    expect(Object.keys(CAPACIDADES_META).sort()).toEqual([...CAPACIDADES].sort());
    for (const slug of CAPACIDADES) {
      const meta = CAPACIDADES_META[slug];
      expect(meta.slug).toBe(slug);
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.descripcion.length).toBeGreaterThan(0);
      expect(meta.eje.length).toBeGreaterThan(0);
    }
  });
});

describe("capacidades stored por rubro (canónico; 100/100 requerido)", () => {
  it("restaurante stored es byte-idéntico (ancla)", () => {
    expect([...RUBROS.restaurante.capacidades]).toEqual([...RESTAURANTE_CAPACIDADES]);
  });

  it.each(RUBRO_KEYS)("%s stored es válido, sin duplicados y en CAP_ORDER", (key) => {
    const caps = RUBROS[key].capacidades;
    expect(caps.length).toBeGreaterThan(0);
    expect(caps.every((c) => CAPACIDADES.includes(c))).toBe(true);
    expect(new Set(caps).size).toBe(caps.length);
    expect([...caps]).toEqual(CAPACIDADES.filter((c) => caps.includes(c)));
    expect(caps).toContain("catalogo");
    expect(caps).toContain("pagos");
  });

  it.each(RUBRO_KEYS)("%s: sub-entidad implica expedientes", (key) => {
    const def = RUBROS[key];
    if (def.subEntidadLabel) {
      expect(def.capacidades).toContain("expedientes");
    }
  });
});
