// Fase 5 — Verificación multi-rubro + cero 404 estructural.
//
// Complementa `nav-canonico.test.ts` (estructura/gating restaurante·cosmetica·peluqueria):
//  1. Cada `href` del SSOT tiene su `page.tsx` real en `app/(dashboard)/` (salvo el que abre
//     Cmd+K por diseño) ⇒ ningún ítem del sidebar puede dar 404.
//  2. El sidebar cambia por rubro: retail-con-ERP (materiales_construccion) ve Contabilidad y
//     Personas; retail-sin-ERP (ferreteria) NO; y ninguno gastro ve Comandas/Agenda.
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { construirSidebarCanonico, NAV_CANONICO, navLabelCanonico } from "./nav-canonico";
import { getRubroDef } from "./rubros";

const DASHBOARD_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../app/(dashboard)");

/** href (`/cat/sub` o `/dashboard`) → ruta esperada del `page.tsx` en el App Router. */
const pageFileFor = (href: string): string =>
  resolve(DASHBOARD_DIR, `.${href}`, "page.tsx");

/** Única excepción: abre el Command Palette, no navega a una ruta. */
const SIN_PAGINA = new Set(["inicio-accesos"]);

const catsVisibles = (rubroKey: string): string[] =>
  construirSidebarCanonico(getRubroDef(rubroKey)).map((c) => c.id);
const idsVisibles = (rubroKey: string): Set<string> =>
  new Set(construirSidebarCanonico(getRubroDef(rubroKey)).flatMap((c) => c.subs.map((s) => s.id)));

describe("cero 404 estructural — cada href del SSOT tiene page.tsx", () => {
  const subs = NAV_CANONICO.flatMap((c) => c.subs);

  it.each(subs.filter((s) => !SIN_PAGINA.has(s.id)).map((s) => [s.id, s.href] as const))(
    "%s (%s) existe en app/(dashboard)",
    (_id, href) => {
      expect(existsSync(pageFileFor(href))).toBe(true);
    },
  );

  it("la única sub sin página es la que abre Cmd+K", () => {
    const sinPagina = subs.filter((s) => !existsSync(pageFileFor(s.href))).map((s) => s.id);
    expect(sinPagina).toEqual(["inicio-accesos"]);
  });
});

describe("gating multi-rubro — retail con ERP vs sin ERP", () => {
  it("materiales_construccion (con contabilidad+rrhh) SÍ ve Contabilidad y Personas", () => {
    const cats = catsVisibles("materiales_construccion");
    expect(cats).toContain("contabilidad");
    expect(cats).toContain("rrhh");
    expect(cats).toContain("compras");
    expect(cats).toContain("inventario");
    // Retail sin agenda ni cocina ni producción ni activos fijos.
    expect(cats).not.toContain("produccion");
    expect(cats).not.toContain("activos");
    expect(cats).not.toContain("agenda");
    expect(idsVisibles("materiales_construccion").has("ped-comandas")).toBe(false);
  });

  it("ferreteria (mismo sector, sin ERP) NO ve Contabilidad ni Personas, sí Compras/Inventario", () => {
    const cats = catsVisibles("ferreteria");
    expect(cats).not.toContain("contabilidad");
    expect(cats).not.toContain("rrhh");
    expect(cats).toContain("compras");
    expect(cats).toContain("inventario");
    expect(cats).toContain("catalogo");
  });

  it("cosmetica_belleza: Compras/Inventario/Fidelización sí; Comandas/Agenda/Producción no", () => {
    const cats = catsVisibles("cosmetica_belleza");
    const ids = idsVisibles("cosmetica_belleza");
    expect(cats).toContain("compras");
    expect(cats).toContain("inventario");
    expect(ids.has("cnt-fidelizacion")).toBe(true);
    expect(ids.has("ped-comandas")).toBe(false);
    expect(cats).not.toContain("agenda");
    expect(cats).not.toContain("produccion");
  });
});

// Evidencia impresa (Fase 5, Paso 2): sidebar por rubro. Corre siempre; documenta el gating.
describe("evidencia — sidebar por rubro", () => {
  it("imprime categorías/subs visibles por rubro", () => {
    const rubros = [
      "restaurante",
      "cosmetica_belleza",
      "peluqueria",
      "ferreteria",
      "materiales_construccion",
    ];
    const lineas: string[] = [];
    for (const key of rubros) {
      const rubro = getRubroDef(key);
      const sidebar = construirSidebarCanonico(rubro);
      const nSubs = sidebar.reduce((n, c) => n + c.subs.length, 0);
      lineas.push(`\n▸ ${key} — ${sidebar.length} categorías, ${nSubs} subs`);
      for (const cat of sidebar) {
        const subs = cat.subs.map((s) => navLabelCanonico(s, rubro)).join(", ");
        lineas.push(`   ${cat.num} ${cat.label}: ${subs}`);
      }
      // Toda categoría visible tiene ≥1 sub (invariante del builder).
      expect(sidebar.every((c) => c.subs.length > 0)).toBe(true);
    }
    // eslint-disable-next-line no-console
    console.log(lineas.join("\n"));
  });
});
