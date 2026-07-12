// Estructura del SSOT canónico + gating/dedup por rubro. No usa números mágicos donde
// puede derivar del propio módulo; los invariantes de forma (17 cats, hrefs, ids únicos)
// se comprueban programáticamente.
import { describe, expect, it } from "vitest";
import {
  construirSidebarCanonico,
  NAV_CANONICO,
  navItemsFlatCanonico,
  navLabelCanonico,
  type NavSubC,
} from "./nav-canonico";
import { getRubroDef, plural } from "./rubros";

const ALL_SUBS = NAV_CANONICO.flatMap((c) => c.subs);
const subById = (id: string): NavSubC => {
  const sub = ALL_SUBS.find((s) => s.id === id);
  if (!sub) throw new Error(`sub ${id} no existe`);
  return sub;
};
const idsVisibles = (rubroKey: string): Set<string> =>
  new Set(construirSidebarCanonico(getRubroDef(rubroKey)).flatMap((c) => c.subs.map((s) => s.id)));

describe("NAV_CANONICO — estructura", () => {
  it("tiene 17 categorías con num '01'..'17' único y ordenado", () => {
    expect(NAV_CANONICO).toHaveLength(17);
    const nums = NAV_CANONICO.map((c) => c.num);
    expect(nums).toEqual(Array.from({ length: 17 }, (_, i) => String(i + 1).padStart(2, "0")));
    expect(new Set(nums).size).toBe(17);
  });

  it("todo sub id es único global", () => {
    const ids = ALL_SUBS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("todo href empieza con '/' y matchea /categoria/subcategoria (salvo /dashboard)", () => {
    for (const sub of ALL_SUBS) {
      expect(sub.href.startsWith("/")).toBe(true);
      if (sub.href === "/dashboard") continue;
      expect(sub.href).toMatch(/^\/[a-z0-9-]+\/[a-z0-9-]+$/);
    }
  });

  it("todo href es único (rutas anidadas ⇒ sin dedup por href)", () => {
    const hrefs = ALL_SUBS.map((s) => s.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("toda categoría con id igual al primer segmento de sus hrefs anidados", () => {
    for (const cat of NAV_CANONICO) {
      for (const sub of cat.subs) {
        if (sub.href === "/dashboard") continue;
        expect(sub.href.split("/")[1]).toBe(cat.id);
      }
    }
  });
});

describe("construirSidebarCanonico — restaurante (jerga gastro + gating)", () => {
  const restaurante = getRubroDef("restaurante");
  const visibles = idsVisibles("restaurante");

  it("incluye Comandas, Mesas y Carta con jerga gastro", () => {
    expect(visibles.has("ped-comandas")).toBe(true);
    expect(visibles.has("ped-mesas")).toBe(true);
    expect(visibles.has("cat-productos")).toBe(true);
    expect(navLabelCanonico(subById("cat-productos"), restaurante)).toBe("Carta & Menu");
    expect(navLabelCanonico(subById("ped-comandas"), restaurante)).toBe("Comandas / KDS");
    expect(navLabelCanonico(subById("ped-mesas"), restaurante)).toBe("Mesas");
    expect(navLabelCanonico(subById("agenda-reservas"), restaurante)).toBe("Reservaciones");
  });

  it("NO incluye Contabilidad, Producción, Activos fijos, RRHH, Compras", () => {
    const cats = construirSidebarCanonico(restaurante).map((c) => c.id);
    expect(cats).not.toContain("contabilidad");
    expect(cats).not.toContain("produccion");
    expect(cats).not.toContain("activos");
    expect(cats).not.toContain("rrhh");
    expect(cats).not.toContain("compras");
  });
});

describe("construirSidebarCanonico — cosmetica_belleza", () => {
  const visibles = idsVisibles("cosmetica_belleza");

  it("NO muestra Comandas ni Producción; SÍ Catálogo", () => {
    expect(visibles.has("ped-comandas")).toBe(false);
    const cats = construirSidebarCanonico(getRubroDef("cosmetica_belleza")).map((c) => c.id);
    expect(cats).not.toContain("produccion");
    expect(cats).toContain("catalogo");
  });
});

describe("dedup recurso/mesas", () => {
  it("restaurante (con mesas) NO muestra agenda-recursos", () => {
    expect(idsVisibles("restaurante").has("agenda-recursos")).toBe(false);
  });

  it("un rubro con agenda sin mesas (peluqueria) muestra agenda-recursos y no ped-mesas", () => {
    const visibles = idsVisibles("peluqueria");
    expect(visibles.has("agenda-recursos")).toBe(true);
    expect(visibles.has("ped-mesas")).toBe(false);
  });

  it("agenda-recursos usa plural(recurso) como label fuera de restaurante", () => {
    const peluqueria = getRubroDef("peluqueria");
    expect(navLabelCanonico(subById("agenda-recursos"), peluqueria)).toBe(
      plural(peluqueria.labels.recurso),
    );
  });
});

describe("visibilidad de categoría ⟺ ≥1 sub visible", () => {
  it("ninguna categoría visible queda con subs vacíos", () => {
    for (const cat of construirSidebarCanonico(getRubroDef("restaurante"))) {
      expect(cat.subs.length).toBeGreaterThan(0);
    }
  });

  it("la lista plana solo contiene subs de categorías visibles", () => {
    const flat = navItemsFlatCanonico(getRubroDef("restaurante"));
    const visibles = idsVisibles("restaurante");
    for (const { sub } of flat) expect(visibles.has(sub.id)).toBe(true);
    expect(flat.length).toBe(visibles.size);
  });
});
