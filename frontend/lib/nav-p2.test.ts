// Cobertura del cableado P2 → dashboard (auto-escala: cuenta contra el árbol real
// y contra el filesystem de app/(dashboard)/ — nunca contra números mágicos).
import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CANONICAL_SUB_BY_HREF,
  NAV_TREE_ICONS,
  NAV_TREE_ROUTES,
  esSubActivaP2,
  getVisibleNavGroupsP2,
  getVisibleNavItemsFlatP2,
  hrefParaSub,
  remapLegacyFavoriteIds,
} from "./nav-p2";
import { NAV_TREE_P2 } from "./nav-tree";
import { getRubroDef, plural } from "./rubros";

const ALL_SUB_IDS = NAV_TREE_P2.flatMap((c) => c.subs.map((s) => s.id));
const ROUTES: Record<string, string | null> = NAV_TREE_ROUTES;
const DASHBOARD_DIR = join(process.cwd(), "app", "(dashboard)");

describe("NAV_TREE_ROUTES — cobertura (auto-escala con el árbol)", () => {
  it("cubre exactamente los subs del árbol P2 (sin faltantes ni huérfanos)", () => {
    expect(Object.keys(NAV_TREE_ROUTES).sort()).toEqual([...ALL_SUB_IDS].sort());
  });

  it("toda ruta no-null apunta a un directorio real de app/(dashboard)/", () => {
    for (const [sub, ruta] of Object.entries(ROUTES)) {
      if (ruta === null) continue;
      expect(existsSync(join(DASHBOARD_DIR, ruta.slice(1))), `${sub} → ${ruta}`).toBe(true);
    }
  });

  it("hrefParaSub: null ⇒ /proximamente/<sub>; no-null ⇒ la ruta real", () => {
    expect(hrefParaSub("resumen")).toBe("/dashboard");
    expect(hrefParaSub("accesos-rapidos")).toBe("/proximamente/accesos-rapidos");
  });
});

describe("NAV_TREE_ICONS — cobertura", () => {
  it("todo sub del árbol tiene entrada de ícono", () => {
    expect(Object.keys(NAV_TREE_ICONS).sort()).toEqual([...ALL_SUB_IDS].sort());
  });
});

describe("CANONICAL_SUB_BY_HREF — desambiguación de rutas compartidas", () => {
  it("cubre exactamente los hrefs con >1 sub (computado del crosswalk, no hardcodeado)", () => {
    const porHref = new Map<string, string[]>();
    for (const [sub, ruta] of Object.entries(ROUTES)) {
      if (!ruta) continue;
      porHref.set(ruta, [...(porHref.get(ruta) ?? []), sub]);
    }
    const duplicadas = [...porHref.entries()]
      .filter(([, subs]) => subs.length > 1)
      .map(([href]) => href);
    expect(Object.keys(CANONICAL_SUB_BY_HREF).sort()).toEqual(duplicadas.sort());
    for (const [href, sub] of Object.entries(CANONICAL_SUB_BY_HREF)) {
      expect(ROUTES[sub], `canónica ${sub} debe mapear a ${href}`).toBe(href);
    }
  });

  it("esSubActivaP2 resalta exactamente UNA fila por ruta compartida (restaurante)", () => {
    const flat = getVisibleNavItemsFlatP2(getRubroDef("restaurante"));
    for (const href of Object.keys(CANONICAL_SUB_BY_HREF)) {
      const activas = flat.filter((f) => esSubActivaP2(href, f.item));
      expect(activas.length, `${href} debe tener 1 sola fila activa`).toBe(1);
    }
  });
});

describe("adaptador P2 — paridad restaurante (nivel RUTA)", () => {
  it("toda ruta del sidebar actual de restaurante sigue alcanzable desde P2", () => {
    const hrefs = new Set(
      getVisibleNavItemsFlatP2(getRubroDef("restaurante")).map((f) => f.item.href),
    );
    // Rutas del nav viejo para restaurante. /sudamerica-ia y /ia se reubican en Ola 2
    // (TopBar/Cmd+K — decisión Fase 0); /inventario sigue oculto igual que hoy (sin cap).
    const rutasHoy = [
      "/entrenar-ia",
      "/prospectos",
      "/comandas",
      "/ventas",
      "/mesas",
      "/reservaciones",
      "/carta",
      "/reportes",
      "/leads",
      "/billing",
      "/equipo",
      "/configuracion",
    ];
    for (const ruta of rutasHoy) {
      expect(hrefs.has(ruta), `${ruta} debe seguir alcanzable`).toBe(true);
    }
    expect(hrefs.has("/inventario")).toBe(false);
  });

  it("todo ítem visible trae ícono y href navegable (nunca fila rota)", () => {
    for (const rubroKey of ["restaurante", "ferreteria", "peluqueria"] as const) {
      for (const group of getVisibleNavGroupsP2(getRubroDef(rubroKey))) {
        for (const { item } of group.items) {
          expect(item.icon, `${rubroKey}/${item.id} sin ícono`).toBeTruthy();
          expect(item.href.startsWith("/"), `${rubroKey}/${item.id} href inválido`).toBe(true);
        }
      }
    }
  });
});

describe("labels por rubro (decisión Fase 0, opción A) — separado del golden de IDs", () => {
  it("restaurante conserva su jerga gastro en los labels renderizados", () => {
    const flat = getVisibleNavItemsFlatP2(getRubroDef("restaurante"));
    const labelDe = (id: string) => flat.find((f) => f.item.id === id)?.label;
    expect(labelDe("productos")).toBe("Carta & Menu");
    expect(labelDe("ordenes")).toBe("Ordenes del Dia");
    expect(labelDe("comandas")).toBe("Comandas / KDS");
    expect(labelDe("mesas-salon")).toBe("Mesas");
    expect(labelDe("reservas-citas")).toBe("Reservaciones");
  });

  it("peluquería: recursos-profesionales usa el label del recurso del rubro", () => {
    const peluqueria = getRubroDef("peluqueria");
    const fila = getVisibleNavItemsFlatP2(peluqueria).find(
      (f) => f.item.id === "recursos-profesionales",
    );
    expect(fila?.label).toBe(plural(peluqueria.labels.recurso));
  });
});

describe("dedupe /mesas — recursos-profesionales solo para agenda SIN mesas", () => {
  it("restaurante (mesas+agenda) no ve recursos-profesionales; sí mesas-salon", () => {
    const ids = getVisibleNavItemsFlatP2(getRubroDef("restaurante")).map((f) => f.item.id);
    expect(ids).not.toContain("recursos-profesionales");
    expect(ids).toContain("mesas-salon");
  });

  it("peluquería (agenda sin mesas) sí ve recursos-profesionales; no mesas-salon", () => {
    const ids = getVisibleNavItemsFlatP2(getRubroDef("peluqueria")).map((f) => f.item.id);
    expect(ids).toContain("recursos-profesionales");
    expect(ids).not.toContain("mesas-salon");
  });
});

describe("favoritos legacy → P2 (LEGACY_FAV_ID_MAP)", () => {
  it("remapea ids viejos, descarta los sin sub y dedupea preservando orden", () => {
    expect(
      remapLegacyFavoriteIds(["carta", "comandas", "sudamerica-ia", "ia", "entrenar-ia", "ventas"]),
    ).toEqual(["productos", "comandas", "respuestas-ia", "ordenes"]);
  });

  it("ids P2 ya migrados pasan intactos (idempotente)", () => {
    expect(remapLegacyFavoriteIds(["productos", "directorio"])).toEqual([
      "productos",
      "directorio",
    ]);
  });
});

describe("huérfanas fuera del sidebar P2 (reubicadas — decisión Fase 0)", () => {
  it("ningún rubro lista /sudamerica-ia, /ia, /pipeline, /roi, /productos ni /perfil en el nav P2", () => {
    // /sudamerica-ia→TopBar+Cmd+K · /ia,/roi,/pipeline→Cmd+K · /productos→redirect /carta ·
    // /perfil→Menu de cuenta del footer. Si un href de estos reaparece, es drift.
    const huerfanas = ["/sudamerica-ia", "/ia", "/pipeline", "/roi", "/productos", "/perfil"];
    for (const rubroKey of ["restaurante", "ferreteria", "peluqueria", "veterinaria"] as const) {
      const hrefs = new Set(
        getVisibleNavItemsFlatP2(getRubroDef(rubroKey)).map((f) => f.item.href),
      );
      for (const huerfana of huerfanas) {
        expect(hrefs.has(huerfana), `${rubroKey} no debe listar ${huerfana}`).toBe(false);
      }
    }
  });
});

describe("≥3 rubros no-gastro renderizan navegación distinta y correcta", () => {
  it("peluquería / ferretería / veterinaria proyectan sidebars diferentes", () => {
    const proyeccion = (key: string) =>
      JSON.stringify(
        getVisibleNavGroupsP2(getRubroDef(key)).map((g) => [g.key, g.items.map((i) => i.item.id)]),
      );
    const peluqueria = proyeccion("peluqueria");
    const ferreteria = proyeccion("ferreteria");
    const veterinaria = proyeccion("veterinaria");
    expect(peluqueria).not.toBe(ferreteria);
    expect(ferreteria).not.toBe(veterinaria);
    expect(peluqueria).not.toBe(veterinaria);
    // Y ninguna es la de restaurante (nav propio por rubro, no herencia gastro).
    const restaurante = proyeccion("restaurante");
    for (const p of [peluqueria, ferreteria, veterinaria]) {
      expect(p).not.toBe(restaurante);
    }
  });
});
