import { describe, expect, it } from "vitest";
import {
  NAV_GROUPS,
  getVisibleNavGroups,
  getVisibleNavItemsFlat,
  isNavItemVisible,
} from "./nav-config";
import { getRubroDef } from "./rubros";

const restaurante = getRubroDef("restaurante");
const ferreteria = getRubroDef("ferreteria");
const peluqueria = getRubroDef("peluqueria");

describe("nav-config — restaurante (byte-identidad del Sidebar actual)", () => {
  it("expone exactamente los mismos labels de hoy, agrupados en el mismo orden", () => {
    const groups = getVisibleNavGroups(restaurante);
    expect(groups.map((g) => g.items.map((i) => i.label))).toEqual([
      ["Copiloto Admin", "IA", "Configuración IA"],
      ["Conversaciones IA"],
      ["Comandas / KDS", "Ordenes del Dia", "Mesas", "Reservaciones"],
      ["Carta & Menu"],
      ["Reportes", "Clientes", "Planes & Billing", "Equipo", "Configuracion"],
    ]);
  });

  it("usa nombres de grupo neutros (rediseño) — ya no hay pilares gastronómicos", () => {
    const groups = getVisibleNavGroups(restaurante);
    expect(groups.map((g) => g.label)).toEqual([
      "Inteligencia",
      "Conversaciones",
      "Operación",
      "Catálogo",
      "Negocio",
    ]);
  });

  it("Inventario sigue oculto para restaurante (F3: módulo inventario OFF, sin cambios)", () => {
    const flat = getVisibleNavItemsFlat(restaurante);
    expect(flat.some(({ item }) => item.id === "inventario")).toBe(false);
  });
});

const GASTRO_WORDS = [
  "comanda",
  "kds",
  "carta",
  "menú",
  "menu",
  "mesa",
  "reserva",
  "cocina",
  "plato",
  "chef",
  "gastronom",
];

function containsGastroWord(text: string): boolean {
  const lower = text.toLowerCase();
  return GASTRO_WORDS.some((word) => lower.includes(word));
}

describe("nav-config — rubro sin módulos gastro (ferretería)", () => {
  const flat = getVisibleNavItemsFlat(ferreteria);
  const groups = getVisibleNavGroups(ferreteria);

  it("no muestra Comandas/KDS, Mesas ni Reservaciones (módulos gastro apagados)", () => {
    const ids = flat.map(({ item }) => item.id);
    expect(ids).not.toContain("comandas");
    expect(ids).not.toContain("mesas");
    expect(ids).not.toContain("reservaciones");
  });

  it("ningún label visible contiene palabras gastro", () => {
    for (const { label } of flat) {
      expect(containsGastroWord(label)).toBe(false);
    }
  });

  it("ninguna sección (grupo) contiene palabras gastro en su nombre", () => {
    for (const group of groups) {
      expect(containsGastroWord(group.label)).toBe(false);
    }
  });

  it("Carta & Menu se renombra a la etiqueta neutra del rubro (Catálogo)", () => {
    const carta = flat.find(({ item }) => item.id === "carta");
    expect(carta?.label).toBe(ferreteria.labels.catalogo);
    expect(carta?.label.toLowerCase()).not.toContain("carta");
  });

  it("Inventario sí aparece (ferretería tiene capacidad inventario activa)", () => {
    expect(flat.some(({ item }) => item.id === "inventario")).toBe(true);
  });
});

describe("nav-config — gating por capacidad/flag oculta ítems", () => {
  it("isNavItemVisible respeta la capacidad declarada del ítem", () => {
    const comandasItem = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.id === "comandas");
    if (!comandasItem) throw new Error("fixture: ítem 'comandas' no encontrado en NAV_GROUPS");
    expect(isNavItemVisible(comandasItem, "restaurante")).toBe(true);
    expect(isNavItemVisible(comandasItem, "ferreteria")).toBe(false);
  });

  it("peluquería: gating parcial — mantiene agenda/recurso pero oculta comandas", () => {
    const ids = getVisibleNavItemsFlat(peluqueria).map(({ item }) => item.id);
    expect(ids).toContain("mesas");
    expect(ids).toContain("reservaciones");
    expect(ids).not.toContain("comandas");
  });

  it("ítems sin capacidad (p.ej. Reportes) son visibles sin importar el rubro", () => {
    for (const rubro of [restaurante, ferreteria, peluqueria]) {
      const ids = getVisibleNavItemsFlat(rubro).map(({ item }) => item.id);
      expect(ids).toContain("reportes");
    }
  });
});
