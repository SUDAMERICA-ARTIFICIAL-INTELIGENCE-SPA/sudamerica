// SSOT de navegación — arquitectura neutra 100+ rubros (Fase 3).
//
// Un único lugar declara ítems/grupos de navegación; Sidebar y CommandPalette
// derivan de aquí en vez de mantener listas duplicadas. El gating por capacidad
// (`tieneCapacidad`) y el renombrado por rubro (`rubroLabel`) se resuelven acá,
// así ambos consumidores quedan automáticamente en sync.
//
// Regla de oro: para restaurante (RUBRO_DEFAULT) las etiquetas de ÍTEM deben
// quedar byte-idénticas a las de siempre (ver lib/nav-config.test.ts). Los
// nombres de GRUPO son neutros y nuevos para todos los rubros — es el rediseño.

import {
  IconArmchair,
  IconBook2,
  IconBrandWhatsapp,
  IconCalendar,
  IconChartBar,
  IconChefHat,
  IconCreditCard,
  IconCurrencyDollar,
  IconPackage,
  IconRobot,
  IconSchool,
  IconSettings,
  IconSparkles,
  IconUsers,
  IconUsersGroup,
} from "@tabler/icons-react";
import type { ComponentType } from "react";
import type { Capacidad } from "./capacidades";
import { RUBRO_DEFAULT, type RubroDef, getRubroDef, plural, tieneCapacidad } from "./rubros";

/** Icono de navegación — cualquier componente de @tabler/icons-react. */
export type NavIcon = ComponentType<{ size?: number }>;

export type NavGroupKey = "inteligencia" | "conversaciones" | "operacion" | "catalogo" | "negocio";

export interface NavItemDef {
  /** ID estable (= href sin "/"). Usado como key de lista y para favoritos. */
  id: string;
  label: string;
  href: string;
  icon: NavIcon;
  /** Capacidad que habilita este ítem; si falta, siempre visible. */
  cap?: Capacidad;
  /** Flag de dato que habilita este ítem (recurso físico reservable). */
  flag?: "recurso";
  /** Etiqueta por rubro (solo se aplica a rubros ≠ restaurante). */
  rubroLabel?: (r: RubroDef) => string;
}

export interface NavGroupDef {
  key: NavGroupKey;
  label: string;
  items: readonly NavItemDef[];
}

export const NAV_GROUPS: readonly NavGroupDef[] = [
  {
    key: "inteligencia",
    label: "Inteligencia",
    items: [
      { id: "sudamerica-ia", label: "Copiloto Admin", href: "/sudamerica-ia", icon: IconSparkles },
      { id: "ia", label: "IA", href: "/ia", icon: IconRobot },
      { id: "entrenar-ia", label: "Configuración IA", href: "/entrenar-ia", icon: IconSchool },
    ],
  },
  {
    key: "conversaciones",
    label: "Conversaciones",
    items: [
      {
        id: "prospectos",
        label: "Conversaciones IA",
        href: "/prospectos",
        icon: IconBrandWhatsapp,
      },
    ],
  },
  {
    key: "operacion",
    label: "Operación",
    items: [
      {
        id: "comandas",
        label: "Comandas / KDS",
        href: "/comandas",
        icon: IconChefHat,
        cap: "mesas",
      },
      { id: "ventas", label: "Ordenes del Dia", href: "/ventas", icon: IconCurrencyDollar },
      {
        id: "mesas",
        label: "Mesas",
        href: "/mesas",
        icon: IconArmchair,
        flag: "recurso",
        rubroLabel: (r) => plural(r.labels.recurso),
      },
      {
        id: "reservaciones",
        label: "Reservaciones",
        href: "/reservaciones",
        icon: IconCalendar,
        cap: "agenda",
        rubroLabel: (r) => plural(r.labels.agenda),
      },
    ],
  },
  {
    key: "catalogo",
    label: "Catálogo",
    items: [
      {
        id: "carta",
        label: "Carta & Menu",
        href: "/carta",
        icon: IconBook2,
        cap: "catalogo",
        rubroLabel: (r) => r.labels.catalogo,
      },
      {
        id: "inventario",
        label: "Inventario",
        href: "/inventario",
        icon: IconPackage,
        cap: "inventario",
      },
    ],
  },
  {
    key: "negocio",
    label: "Negocio",
    items: [
      { id: "reportes", label: "Reportes", href: "/reportes", icon: IconChartBar },
      { id: "leads", label: "Clientes", href: "/leads", icon: IconUsers },
      { id: "billing", label: "Planes & Billing", href: "/billing", icon: IconCreditCard },
      { id: "equipo", label: "Equipo", href: "/equipo", icon: IconUsersGroup },
      { id: "configuracion", label: "Configuracion", href: "/configuracion", icon: IconSettings },
    ],
  },
] as const;

/** Etiqueta visible del ítem: estática para restaurante (byte-idéntico), por rubro para el resto. */
export function navItemLabel(item: NavItemDef, rubro: RubroDef): string {
  if (rubro.key === RUBRO_DEFAULT || !item.rubroLabel) return item.label;
  return item.rubroLabel(rubro);
}

/** ¿Ítem visible para este rubro? (gating por capacidad/flag; restaurante = sin cambios). */
export function isNavItemVisible(item: NavItemDef, rubroKey: RubroDef["key"]): boolean {
  if (item.cap && !tieneCapacidad(rubroKey, item.cap)) return false;
  if (item.flag === "recurso" && !getRubroDef(rubroKey).recurso) return false;
  return true;
}

export interface VisibleNavItem {
  item: NavItemDef;
  label: string;
}

export interface VisibleNavGroup {
  key: NavGroupKey;
  label: string;
  items: VisibleNavItem[];
}

/** Deriva las secciones visibles para un rubro: filtra por módulo y resuelve labels. */
export function getVisibleNavGroups(rubro: RubroDef): VisibleNavGroup[] {
  return NAV_GROUPS.map((group) => ({
    key: group.key,
    label: group.label,
    items: group.items
      .filter((item) => isNavItemVisible(item, rubro.key))
      .map((item) => ({ item, label: navItemLabel(item, rubro) })),
  })).filter((group) => group.items.length > 0);
}

export interface VisibleNavItemFlat extends VisibleNavItem {
  groupLabel: string;
}

/** Lista plana de todos los ítems visibles (usado por CommandPalette y favoritos). */
export function getVisibleNavItemsFlat(rubro: RubroDef): VisibleNavItemFlat[] {
  return getVisibleNavGroups(rubro).flatMap((group) =>
    group.items.map(({ item, label }) => ({ item, label, groupLabel: group.label })),
  );
}
