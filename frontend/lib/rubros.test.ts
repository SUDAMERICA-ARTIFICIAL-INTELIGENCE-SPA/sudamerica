import { describe, expect, it } from "vitest";
import { CAPACIDADES } from "./capacidades";
import {
  PRIMITIVAS,
  RUBROS,
  RUBRO_DEFAULT,
  RUBRO_OPTIONS,
  type RubroKey,
  getRubroDef,
  resolveRubro,
  tieneCapacidad,
} from "./rubros";

// Deriva del SSOT para auto-escalar con cada rubro nuevo (data-only).
const RUBRO_KEYS: RubroKey[] = Object.keys(RUBROS) as RubroKey[];

describe("resolveRubro — default / backwards-compatibility", () => {
  it("defaults to restaurante", () => {
    expect(RUBRO_DEFAULT).toBe("restaurante");
    expect(resolveRubro(null)).toBe("restaurante");
    expect(resolveRubro(undefined)).toBe("restaurante");
    expect(resolveRubro({})).toBe("restaurante");
    expect(resolveRubro({ rubro: null })).toBe("restaurante");
  });

  it("reads the config key", () => {
    expect(resolveRubro({ rubro: "peluqueria" })).toBe("peluqueria");
    expect(resolveRubro({ rubro: "ferreteria" })).toBe("ferreteria");
  });

  it("is fail-safe on unknown rubro", () => {
    expect(resolveRubro({ rubro: "rubro_inexistente" })).toBe("restaurante");
    expect(getRubroDef("rubro_inexistente").key).toBe("restaurante");
    expect(getRubroDef(null).key).toBe("restaurante");
  });
});

describe("contract completeness", () => {
  it.each(RUBRO_KEYS)("%s defines a label for every primitiva", (key) => {
    const def = RUBROS[key];
    expect(Object.keys(def.labels).sort()).toEqual([...PRIMITIVAS].sort());
    expect(Object.values(def.labels).every((v) => typeof v === "string" && v.length > 0)).toBe(
      true,
    );
  });

  it.each(RUBRO_KEYS)("%s capacidades are a subset and seeds are present", (key) => {
    const def = RUBROS[key];
    expect(def.capacidades.every((c) => CAPACIDADES.includes(c))).toBe(true);
    expect(def.categoriasSemilla.length).toBeGreaterThanOrEqual(1);
    expect(def.capacidades).toContain("catalogo");
    expect(def.capacidades).toContain("pagos");
  });

  it("RUBRO_OPTIONS exposes every rubro for the onboarding selector", () => {
    expect(RUBRO_OPTIONS.map((o) => o.value).sort()).toEqual([...RUBRO_KEYS].sort());
  });
});

describe("per-rubro semantics (7 ejes)", () => {
  it("restaurante keeps full operativa", () => {
    for (const c of ["mesas", "agenda", "delivery", "pedidos"] as const) {
      expect(tieneCapacidad("restaurante", c)).toBe(true);
    }
    expect(RUBROS.restaurante.recurso).toBe(true);
    expect(RUBROS.restaurante.labels.recurso).toBe("Mesa");
    expect(RUBROS.restaurante.labels.orden).toBe("Comanda");
    // F3: inventario (stock por ítem) OFF en restaurante → el ítem de nav
    // "Inventario" no aparece y la UI queda byte-idéntica.
    expect(tieneCapacidad("restaurante", "inventario")).toBe(false);
  });

  it("peluqueria = servicio-con-cita, sin cocina", () => {
    expect(tieneCapacidad("peluqueria", "agenda")).toBe(true);
    expect(RUBROS.peluqueria.recurso).toBe(true);
    expect(tieneCapacidad("peluqueria", "mesas")).toBe(false);
    expect(tieneCapacidad("peluqueria", "delivery")).toBe(false);
    expect(tieneCapacidad("peluqueria", "inventario")).toBe(false);
    expect(RUBROS.peluqueria.labels.item).toBe("Servicio");
  });

  it("ferreteria = retail-con-stock, sin agenda", () => {
    expect(tieneCapacidad("ferreteria", "inventario")).toBe(true);
    expect(tieneCapacidad("ferreteria", "agenda")).toBe(false);
    expect(tieneCapacidad("ferreteria", "mesas")).toBe(false);
  });

  it("veterinaria = servicio-con-cita + sub-entidad (F6)", () => {
    expect(tieneCapacidad("veterinaria", "expedientes")).toBe(true);
    expect(tieneCapacidad("veterinaria", "agenda")).toBe(true);
    expect(tieneCapacidad("veterinaria", "mesas")).toBe(false);
    expect(RUBROS.veterinaria.subEntidadLabel).toBe("Mascota");
    // Invariante (relajada en Etapa B): label de sub-entidad ⟹ capacidad expedientes.
    for (const key of RUBRO_KEYS) {
      if (RUBROS[key].subEntidadLabel !== undefined) {
        expect(RUBROS[key].capacidades).toContain("expedientes");
      }
    }
  });
});

describe("F2: tenant.config → rubro + gating de navegación (Sidebar)", () => {
  it("resolveRubro lee el rubro desde un config de tenant completo", () => {
    const config: Record<string, unknown> = {
      sector: "salud_estetica",
      rubro: "peluqueria",
      onboarding: { required: false },
    };
    expect(resolveRubro(config)).toBe("peluqueria");
  });

  it("restaurante conserva TODOS los ítems de nav (sidebar byte-idéntico)", () => {
    for (const c of ["mesas", "agenda", "catalogo", "pedidos"] as const) {
      expect(tieneCapacidad("restaurante", c)).toBe(true);
    }
    expect(RUBROS.restaurante.recurso).toBe(true);
  });

  it("peluqueria oculta cocina; mantiene recurso (Silla) y agenda (Cita)", () => {
    expect(tieneCapacidad("peluqueria", "mesas")).toBe(false);
    expect(RUBROS.peluqueria.recurso).toBe(true);
    expect(tieneCapacidad("peluqueria", "agenda")).toBe(true);
    expect(tieneCapacidad("peluqueria", "catalogo")).toBe(true);
  });

  it("ferreteria oculta cocina, agenda y recurso; mantiene catálogo", () => {
    expect(tieneCapacidad("ferreteria", "mesas")).toBe(false);
    expect(tieneCapacidad("ferreteria", "agenda")).toBe(false);
    expect(RUBROS.ferreteria.recurso ?? false).toBe(false);
    expect(tieneCapacidad("ferreteria", "catalogo")).toBe(true);
  });
});
