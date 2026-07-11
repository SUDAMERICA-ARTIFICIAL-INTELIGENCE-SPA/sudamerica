// Fuente P2 del shell (Sidebar/TopBar/CommandPalette) tras el flag NEXT_PUBLIC_NAV_P2.
//
// Cablea el árbol NAV_TREE_P2 (lib/nav-tree.ts — 11 categorías gateadas por capacidad)
// al render existente SIN reescribirlo: tres mapas de datos (ruta, ícono, canónica) +
// adaptadores que producen la misma forma que el shell consume hoy desde lib/nav-config.ts.
//
// Crosswalk autoritativo: PROMPT_dashboard_multirubro_p2.md §0.1. Los subs sin ruta real
// arrancan en `null` (⇒ /proximamente/<sub>) hasta que la ola que construye ese stub la
// actualice. La exhaustividad (todo sub del árbol tiene ruta e ícono) la fija
// lib/nav-p2.test.ts con conteo programático contra el árbol y contra app/(dashboard)/.

import {
  IconAdjustments,
  IconArmchair,
  IconArrowBackUp,
  IconAward,
  IconBell,
  IconBook2,
  IconBrandWhatsapp,
  IconBuildingStore,
  IconBuildingWarehouse,
  IconCalendar,
  IconCalendarEvent,
  IconCalendarStats,
  IconCash,
  IconChartBar,
  IconChecklist,
  IconChefHat,
  IconClock,
  IconCommand,
  IconCreditCard,
  IconCurrencyDollar,
  IconFileInvoice,
  IconFileText,
  IconFiles,
  IconFolderOpen,
  IconFolders,
  IconHeart,
  IconHome,
  IconId,
  IconKey,
  IconLayoutKanban,
  IconMapPin,
  IconNotebook,
  IconPackage,
  IconPhoto,
  IconPlug,
  IconPlugConnected,
  IconPuzzle,
  IconReceipt,
  IconReceipt2,
  IconRepeat,
  IconReportMoney,
  IconSchool,
  IconShoppingCart,
  IconSignature,
  IconTags,
  IconTemplate,
  IconTicket,
  IconTool,
  IconToolsKitchen2,
  IconTransfer,
  IconTruck,
  IconUsers,
  IconUsersGroup,
  IconWorld,
} from "@tabler/icons-react";
import type { NavIcon } from "./nav-config";
import { construirSidebarParaRubro } from "./nav-tree";
import { RUBRO_DEFAULT, type RubroDef, plural } from "./rubros";

/** Flag de build (NEXT_PUBLIC_ ⇒ inlined). OFF por default: el shell sigue en nav-config. */
export const NAV_P2_ENABLED = process.env.NEXT_PUBLIC_NAV_P2 === "true";

/**
 * Crosswalk sub P2 → ruta real de app/(dashboard)/ (§0.1). `null` = placeholder
 * (/proximamente/<sub>) hasta que la ola que construya el stub la reemplace.
 */
export const NAV_TREE_ROUTES = {
  // 01 inicio
  resumen: "/dashboard",
  "tareas-del-dia": "/tareas-del-dia",
  notificaciones: "/notificaciones",
  "accesos-rapidos": null,
  // 02 contactos
  directorio: "/leads",
  segmentos: "/leads",
  "ficha-de-contacto": "/leads",
  expedientes: "/expedientes",
  consentimientos: "/consentimientos",
  // 03 conversaciones
  "bandeja-de-entrada": "/prospectos",
  canales: "/prospectos",
  "respuestas-ia": "/entrenar-ia",
  plantillas: "/plantillas",
  tickets: "/tickets",
  // 04 catalogo
  productos: "/carta",
  servicios: "/carta",
  "variantes-precios": "/carta",
  cotizaciones: "/cotizaciones",
  "planes-membresias": "/planes-membresias",
  "cursos-programas": "/cursos-programas",
  // 05 agenda
  calendario: "/calendario",
  "reservas-citas": "/reservaciones",
  disponibilidad: "/disponibilidad",
  "recursos-profesionales": "/mesas",
  "visitas-terreno": "/visitas-terreno",
  "disponibilidad-activos": "/disponibilidad-activos",
  // 06 pedidos
  ordenes: "/ventas",
  comandas: "/comandas",
  "mesas-salon": "/mesas",
  entregas: "/entregas",
  "proyectos-trabajos": "/proyectos-trabajos",
  devoluciones: "/devoluciones",
  // 07 dinero
  ingresos: "/reportes",
  "cobros-pagos": "/cobros-pagos",
  facturacion: "/facturacion",
  "suscripciones-recurrencia": "/suscripciones-recurrencia",
  "reportes-financieros": "/reportes",
  // 08 inventario
  existencias: "/inventario",
  movimientos: "/movimientos",
  bodegas: "/bodegas",
  "ordenes-compra": "/ordenes-compra",
  "produccion-recetas": "/produccion-recetas",
  "activos-arriendo": "/activos-arriendo",
  // 09 documentos
  archivos: "/archivos",
  contratos: "/contratos",
  "consentimientos-firmados": "/consentimientos-firmados",
  "documentos-tributarios": "/documentos-tributarios",
  "expedientes-casos": "/expedientes-casos",
  // 10 contenido
  campanas: "/campanas",
  "biblioteca-medios": "/biblioteca-medios",
  "catalogo-publico": "/catalogo-publico",
  "programa-fidelizacion": "/programa-fidelizacion",
  // 11 cuenta
  "perfil-negocio": "/configuracion",
  "equipo-permisos": "/equipo",
  "capacidades-modulos": "/capacidades",
  integraciones: "/integraciones",
  "facturacion-servicio": "/billing",
} satisfies Record<string, string | null>;

/**
 * Ícono por sub (NavSub no trae `icon`; NavItemRow lo exige). Reusa los íconos de
 * nav-config.ts para las rutas reusadas (leads→Users, carta→Book2, mesas→Armchair…).
 */
export const NAV_TREE_ICONS = {
  // 01 inicio
  resumen: IconHome,
  "tareas-del-dia": IconChecklist,
  notificaciones: IconBell,
  "accesos-rapidos": IconCommand,
  // 02 contactos
  directorio: IconUsers,
  segmentos: IconTags,
  "ficha-de-contacto": IconId,
  expedientes: IconFolders,
  consentimientos: IconSignature,
  // 03 conversaciones
  "bandeja-de-entrada": IconBrandWhatsapp,
  canales: IconPlug,
  "respuestas-ia": IconSchool,
  plantillas: IconTemplate,
  tickets: IconTicket,
  // 04 catalogo
  productos: IconBook2,
  servicios: IconTool,
  "variantes-precios": IconAdjustments,
  cotizaciones: IconFileInvoice,
  "planes-membresias": IconAward,
  "cursos-programas": IconNotebook,
  // 05 agenda
  calendario: IconCalendar,
  "reservas-citas": IconCalendarEvent,
  disponibilidad: IconClock,
  "recursos-profesionales": IconArmchair,
  "visitas-terreno": IconMapPin,
  "disponibilidad-activos": IconCalendarStats,
  // 06 pedidos
  ordenes: IconCurrencyDollar,
  comandas: IconChefHat,
  "mesas-salon": IconArmchair,
  entregas: IconTruck,
  "proyectos-trabajos": IconLayoutKanban,
  devoluciones: IconArrowBackUp,
  // 07 dinero
  ingresos: IconChartBar,
  "cobros-pagos": IconCash,
  facturacion: IconReceipt2,
  "suscripciones-recurrencia": IconRepeat,
  "reportes-financieros": IconReportMoney,
  // 08 inventario
  existencias: IconPackage,
  movimientos: IconTransfer,
  bodegas: IconBuildingWarehouse,
  "ordenes-compra": IconShoppingCart,
  "produccion-recetas": IconToolsKitchen2,
  "activos-arriendo": IconKey,
  // 09 documentos
  archivos: IconFiles,
  contratos: IconFileText,
  "consentimientos-firmados": IconSignature,
  "documentos-tributarios": IconReceipt,
  "expedientes-casos": IconFolderOpen,
  // 10 contenido
  campanas: IconChartBar,
  "biblioteca-medios": IconPhoto,
  "catalogo-publico": IconWorld,
  "programa-fidelizacion": IconHeart,
  // 11 cuenta
  "perfil-negocio": IconBuildingStore,
  "equipo-permisos": IconUsersGroup,
  "capacidades-modulos": IconPuzzle,
  integraciones: IconPlugConnected,
  "facturacion-servicio": IconCreditCard,
} satisfies Record<string, NavIcon>;

/**
 * Desambiguación de rutas compartidas por varias subs: UNA sub canónica por href.
 * Active-state/breadcrumb resaltan solo la fila canónica (las demás se diferencian
 * por query/anchor/vista cuando existan).
 */
export const CANONICAL_SUB_BY_HREF = {
  "/carta": "productos",
  "/mesas": "mesas-salon",
  "/leads": "directorio",
  "/prospectos": "bandeja-de-entrada",
  "/reportes": "ingresos",
} satisfies Record<string, string>;

// Vistas ensanchadas para lookup por string sin cast (asignación a supertipo, no `as`).
const ROUTES: Record<string, string | null> = NAV_TREE_ROUTES;
const ICONS: Record<string, NavIcon> = NAV_TREE_ICONS;
const CANONICAS: Record<string, string> = CANONICAL_SUB_BY_HREF;

/** href navegable de una sub: su ruta real, o el placeholder /proximamente/<sub>. */
export function hrefParaSub(subId: string): string {
  return ROUTES[subId] ?? `/proximamente/${subId}`;
}

/**
 * Overrides de label para restaurante (decisión Fase 0, opción A): la jerga gastro
 * actual se conserva tal cual — percepción byte-idéntica en las filas reusadas.
 */
const RESTAURANTE_SUB_LABELS: Record<string, string> = {
  productos: "Carta & Menu",
  ordenes: "Ordenes del Dia",
  comandas: "Comandas / KDS",
  "mesas-salon": "Mesas",
  "reservas-citas": "Reservaciones",
};

/** Labels dinámicos por rubro ≠ restaurante — espejo del rubroLabel de nav-config. */
const LABELS_POR_RUBRO: Record<string, (r: RubroDef) => string> = {
  "recursos-profesionales": (r) => plural(r.labels.recurso),
};

/** Label renderizado de una sub para un rubro (override restaurante > dinámico > genérico P2). */
export function navSubLabelP2(subId: string, labelGenerico: string, rubro: RubroDef): string {
  if (rubro.key === RUBRO_DEFAULT) return RESTAURANTE_SUB_LABELS[subId] ?? labelGenerico;
  return LABELS_POR_RUBRO[subId]?.(rubro) ?? labelGenerico;
}

/**
 * Favoritos fijados con ids del nav viejo → subId P2 (decisión Fase 0: LEGACY_FAV_ID_MAP).
 * "comandas" ya coincide con el subId P2; "sudamerica-ia" no tiene sub (vive en TopBar) → se descarta.
 */
export const LEGACY_FAV_ID_MAP: Record<string, string> = {
  "entrenar-ia": "respuestas-ia",
  ia: "respuestas-ia",
  prospectos: "bandeja-de-entrada",
  ventas: "ordenes",
  mesas: "mesas-salon",
  reservaciones: "reservas-citas",
  carta: "productos",
  inventario: "existencias",
  reportes: "ingresos",
  leads: "directorio",
  billing: "facturacion-servicio",
  equipo: "equipo-permisos",
  configuracion: "perfil-negocio",
};

const SUB_IDS_P2 = new Set(Object.keys(NAV_TREE_ROUTES));

/** Migra una lista de favoritos: remapea ids viejos, descarta los sin sub y dedupea. */
export function remapLegacyFavoriteIds(ids: readonly string[]): string[] {
  const remapped = ids.map((id) => LEGACY_FAV_ID_MAP[id] ?? id).filter((id) => SUB_IDS_P2.has(id));
  return [...new Set(remapped)];
}

// ── Adaptadores: misma forma estructural que VisibleNavGroup/VisibleNavItemFlat
//    de nav-config.ts (NavItemP2 es asignable a NavItemDef), para conservar el render. ──

export interface NavItemP2 {
  /** ID estable = id de sub del árbol P2 (único global — lo garantiza nav-tree.test.ts). */
  id: string;
  label: string;
  href: string;
  icon: NavIcon;
}

export interface VisibleNavItemP2 {
  item: NavItemP2;
  label: string;
}

export interface VisibleNavGroupP2 {
  key: string;
  label: string;
  items: VisibleNavItemP2[];
}

export interface VisibleNavItemFlatP2 extends VisibleNavItemP2 {
  groupLabel: string;
}

const FALLBACK_ICON: NavIcon = IconPuzzle;

/** Sidebar P2: categorías del árbol filtradas por capacidades del rubro, con href e ícono. */
export function getVisibleNavGroupsP2(rubro: RubroDef): VisibleNavGroupP2[] {
  // Dedupe /mesas: `mesas-salon` es la canónica para rubros con cap `mesas`;
  // `recursos-profesionales` queda solo para rubros de agenda SIN mesas.
  const tieneMesas = rubro.capacidades.includes("mesas");
  return construirSidebarParaRubro(rubro)
    .map((categoria) => ({
      key: categoria.id,
      label: categoria.label,
      items: categoria.subs
        .filter((sub) => !(sub.id === "recursos-profesionales" && tieneMesas))
        .map((sub) => {
          const label = navSubLabelP2(sub.id, sub.label, rubro);
          const item: NavItemP2 = {
            id: sub.id,
            label,
            href: hrefParaSub(sub.id),
            icon: ICONS[sub.id] ?? FALLBACK_ICON,
          };
          return { item, label };
        }),
    }))
    .filter((group) => group.items.length > 0);
}

/** Lista plana (TopBar/CommandPalette/favoritos) — espejo de getVisibleNavItemsFlat. */
export function getVisibleNavItemsFlatP2(rubro: RubroDef): VisibleNavItemFlatP2[] {
  return getVisibleNavGroupsP2(rubro).flatMap((group) =>
    group.items.map(({ item, label }) => ({ item, label, groupLabel: group.label })),
  );
}

/** ¿Es esta sub la canónica de su href? (evita 3 entradas → /carta en Cmd+K, etc.). */
export function esSubCanonica(item: Pick<NavItemP2, "id" | "href">): boolean {
  const canonica = CANONICAS[item.href];
  return canonica === undefined || canonica === item.id;
}

/**
 * Active-state P2: prefijo de ruta + regla de sub canónica para rutas compartidas.
 * Compartido por Sidebar y TopBar (antes cada uno duplicaba su isActiveHref local).
 */
export function esSubActivaP2(pathname: string, item: Pick<NavItemP2, "id" | "href">): boolean {
  const activa = pathname === item.href || pathname.startsWith(`${item.href}/`);
  return activa && esSubCanonica(item);
}
