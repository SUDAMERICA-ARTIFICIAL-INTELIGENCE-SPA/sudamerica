// SSOT de navegación canónico (Paso 7) — UN solo módulo con las 17 categorías del §3.
//
// Reemplaza el trío nav-config / nav-tree / nav-p2: cada sub tiene una ruta ANIDADA única
// (`/categoria/subcategoria`), así que NO hace falta CANONICAL_SUB_BY_HREF ni dedup por href.
// El active-state es `pathname === href || pathname.startsWith(href + "/")`.
//
// Esta fase solo crea el módulo + su test de estructura. El Sidebar/CommandPalette se cablean
// en Fase 4. Debe pasar `npm run typecheck`.

import {
  IconActivity,
  IconAdjustments,
  IconArmchair,
  IconArrowBackUp,
  IconArrowDownCircle,
  IconArrowsExchange,
  IconArrowsLeftRight,
  IconArrowUpCircle,
  IconAward,
  IconBarcode,
  IconBeach,
  IconBell,
  IconBook,
  IconBook2,
  IconBrandWhatsapp,
  IconBriefcase,
  IconBuildingBank,
  IconBuildingFactory,
  IconBuildingSkyscraper,
  IconBuildingStore,
  IconBuildingWarehouse,
  IconCalculator,
  IconCalendar,
  IconCalendarEvent,
  IconCalendarStats,
  IconCalendarTime,
  IconCash,
  IconChartArea,
  IconChartBar,
  IconChartPie,
  IconChecklist,
  IconChefHat,
  IconCircleCheck,
  IconClipboardCheck,
  IconClipboardList,
  IconClock,
  IconClockCheck,
  IconCoin,
  IconCommand,
  IconCreditCard,
  IconCurrencyDollar,
  IconFileInvoice,
  IconFileReport,
  IconFiles,
  IconFileText,
  IconFolder,
  IconFolderOpen,
  IconFolders,
  IconHeart,
  IconHome,
  IconId,
  IconKey,
  IconLayoutKanban,
  IconListDetails,
  IconMapPin,
  IconMessageCircle,
  IconNotebook,
  IconPackage,
  IconPackageImport,
  IconPencil,
  IconPhoto,
  IconPlug,
  IconPlugConnected,
  IconPuzzle,
  IconReceipt,
  IconReceipt2,
  IconRepeat,
  IconReportMoney,
  IconSchool,
  IconSettings,
  IconShoppingCart,
  IconSignature,
  IconSitemap,
  IconSpeakerphone,
  IconStar,
  IconTags,
  IconTargetArrow,
  IconTemplate,
  IconTicket,
  IconTool,
  IconTools,
  IconTransfer,
  IconTrash,
  IconTrendingDown,
  IconTrendingUp,
  IconTruck,
  IconUserPlus,
  IconUsers,
  IconUsersGroup,
  IconWorld,
} from "@tabler/icons-react";
import type { ComponentType } from "react";
import type { Capacidad } from "./capacidades";
import { plural, RUBRO_DEFAULT, type RubroDef, tieneCapacidad } from "./rubros";

/** Icono de navegación — cualquier componente de @tabler/icons-react. */
export type NavIcon = ComponentType<{ size?: number }>;

export interface NavSubC {
  /** kebab, ÚNICO global (para keys/tests/favoritos). */
  id: string;
  /** genérico neutro. */
  label: string;
  /** `/categoria/subcategoria` EXACTO de la tabla (o `/dashboard`). */
  href: string;
  icon: NavIcon;
  /** sin cap ⇒ siempre visible dentro de su categoría. */
  cap?: Capacidad;
  /** override por rubro ≠ restaurante (dinámico). */
  rubroLabel?: (r: RubroDef) => string;
  /** override literal para restaurante (jerga gastro). */
  restauranteLabel?: string;
}

export interface NavCatC {
  id: string;
  label: string;
  /** "01".."17". */
  num: string;
  /** hex §3. */
  color: string;
  icon: NavIcon;
  subs: readonly NavSubC[];
}

export const NAV_CANONICO: readonly NavCatC[] = [
  {
    id: "inicio",
    label: "Inicio",
    num: "01",
    color: "#4C6EF5",
    icon: IconHome,
    subs: [
      { id: "resumen", label: "Resumen", href: "/dashboard", icon: IconHome },
      { id: "inicio-actividad", label: "Actividad reciente", href: "/inicio/actividad", icon: IconActivity },
      { id: "inicio-tareas", label: "Tareas del día", href: "/inicio/tareas", icon: IconChecklist },
      { id: "inicio-notificaciones", label: "Notificaciones", href: "/inicio/notificaciones", icon: IconBell },
      { id: "inicio-accesos", label: "Accesos rápidos", href: "/inicio/accesos-rapidos", icon: IconCommand },
    ],
  },
  {
    id: "contactos",
    label: "Contactos",
    num: "02",
    color: "#0099FF",
    icon: IconUsers,
    subs: [
      { id: "contactos-directorio", label: "Directorio", href: "/contactos/directorio", icon: IconUsers },
      { id: "contactos-segmentos", label: "Segmentos", href: "/contactos/segmentos", icon: IconTags },
      { id: "contactos-ficha", label: "Ficha de contacto", href: "/contactos/ficha", icon: IconId },
      { id: "contactos-expedientes", label: "Fichas (Expedientes)", href: "/contactos/expedientes", icon: IconFolders, cap: "expedientes" },
      { id: "contactos-consentimientos", label: "Consentimientos", href: "/contactos/consentimientos", icon: IconSignature, cap: "consentimientos" },
    ],
  },
  {
    id: "conversaciones",
    label: "Conversaciones",
    num: "03",
    color: "#FF4757",
    icon: IconMessageCircle,
    subs: [
      { id: "conv-bandeja", label: "Bandeja de entrada", href: "/conversaciones/bandeja", icon: IconBrandWhatsapp },
      { id: "conv-canales", label: "Canales", href: "/conversaciones/canales", icon: IconPlug },
      { id: "conv-ia", label: "Respuestas de la IA", href: "/conversaciones/ia", icon: IconSchool },
      { id: "conv-plantillas", label: "Plantillas", href: "/conversaciones/plantillas", icon: IconTemplate },
      { id: "conv-tickets", label: "Tickets (Soporte)", href: "/conversaciones/tickets", icon: IconTicket, cap: "soporte" },
    ],
  },
  {
    id: "catalogo",
    label: "Catálogo",
    num: "04",
    color: "#FFB800",
    icon: IconPackage,
    subs: [
      { id: "cat-productos", label: "Productos", href: "/catalogo/productos", icon: IconBook2, cap: "catalogo", restauranteLabel: "Carta & Menu" },
      { id: "cat-servicios", label: "Servicios", href: "/catalogo/servicios", icon: IconTool, cap: "catalogo" },
      { id: "cat-variantes", label: "Variantes y precios", href: "/catalogo/variantes", icon: IconAdjustments, cap: "catalogo" },
      { id: "cat-costos", label: "Costos y márgenes", href: "/catalogo/costos", icon: IconReportMoney, cap: "catalogo" },
      { id: "cat-cotizaciones", label: "Cotizaciones", href: "/catalogo/cotizaciones", icon: IconFileInvoice, cap: "cotizador" },
      { id: "cat-planes", label: "Planes y membresías", href: "/catalogo/planes", icon: IconAward, cap: "suscripciones" },
      { id: "cat-cursos", label: "Cursos y programas", href: "/catalogo/cursos", icon: IconNotebook, cap: "cursos" },
    ],
  },
  {
    id: "agenda",
    label: "Agenda",
    num: "05",
    color: "#20C997",
    icon: IconCalendar,
    subs: [
      { id: "agenda-calendario", label: "Calendario", href: "/agenda/calendario", icon: IconCalendar, cap: "agenda" },
      { id: "agenda-reservas", label: "Reservas y citas", href: "/agenda/reservas", icon: IconCalendarEvent, cap: "agenda", restauranteLabel: "Reservaciones" },
      { id: "agenda-disponibilidad", label: "Disponibilidad", href: "/agenda/disponibilidad", icon: IconClock, cap: "agenda" },
      { id: "agenda-recursos", label: "Recursos y profesionales", href: "/agenda/recursos", icon: IconArmchair, cap: "agenda", rubroLabel: (r) => plural(r.labels.recurso) },
      { id: "agenda-terreno", label: "Visitas en terreno", href: "/agenda/terreno", icon: IconMapPin, cap: "terreno" },
      { id: "agenda-activos", label: "Disponibilidad de activos", href: "/agenda/activos", icon: IconCalendarStats, cap: "arriendos" },
    ],
  },
  {
    id: "pedidos",
    label: "Pedidos",
    num: "06",
    color: "#FA5252",
    icon: IconShoppingCart,
    subs: [
      { id: "ped-ordenes", label: "Órdenes", href: "/pedidos/ordenes", icon: IconCurrencyDollar, cap: "pedidos", restauranteLabel: "Ordenes del Dia" },
      { id: "ped-comandas", label: "Comandas", href: "/pedidos/comandas", icon: IconChefHat, cap: "mesas", restauranteLabel: "Comandas / KDS" },
      { id: "ped-mesas", label: "Mesas y salón", href: "/pedidos/mesas", icon: IconArmchair, cap: "mesas", restauranteLabel: "Mesas" },
      { id: "ped-entregas", label: "Entregas", href: "/pedidos/entregas", icon: IconTruck, cap: "delivery" },
      { id: "ped-devoluciones", label: "Devoluciones", href: "/pedidos/devoluciones", icon: IconArrowBackUp, cap: "pedidos" },
    ],
  },
  {
    id: "dinero",
    label: "Dinero",
    num: "07",
    color: "#00B894",
    icon: IconCoin,
    subs: [
      { id: "din-ingresos", label: "Ingresos", href: "/dinero/ingresos", icon: IconChartBar },
      { id: "din-cobros", label: "Cobros y pagos", href: "/dinero/cobros", icon: IconCash, cap: "pagos" },
      { id: "din-tesoreria", label: "Tesorería", href: "/dinero/tesoreria", icon: IconBuildingBank, cap: "pagos" },
      { id: "din-flujo", label: "Flujo de caja", href: "/dinero/flujo-caja", icon: IconChartArea },
      { id: "din-facturacion", label: "Facturación", href: "/dinero/facturacion", icon: IconReceipt2, cap: "facturacion" },
      { id: "din-suscripciones", label: "Suscripciones", href: "/dinero/suscripciones", icon: IconRepeat, cap: "suscripciones" },
      { id: "din-reportes", label: "Reportes financieros", href: "/dinero/reportes", icon: IconReportMoney },
    ],
  },
  {
    id: "contabilidad",
    label: "Contabilidad",
    num: "08",
    color: "#0CA678",
    icon: IconCalculator,
    subs: [
      { id: "con-plan", label: "Plan de cuentas", href: "/contabilidad/plan-cuentas", icon: IconListDetails, cap: "contabilidad" },
      { id: "con-asientos", label: "Asientos", href: "/contabilidad/asientos", icon: IconPencil, cap: "contabilidad" },
      { id: "con-mayor", label: "Libro mayor", href: "/contabilidad/libro-mayor", icon: IconBook, cap: "contabilidad" },
      { id: "con-cxc", label: "CxC", href: "/contabilidad/cxc", icon: IconArrowDownCircle, cap: "contabilidad" },
      { id: "con-cxp", label: "CxP", href: "/contabilidad/cxp", icon: IconArrowUpCircle, cap: "contabilidad" },
      { id: "con-conciliacion", label: "Conciliación", href: "/contabilidad/conciliacion", icon: IconArrowsLeftRight, cap: "contabilidad" },
      { id: "con-centros", label: "Centros de costo", href: "/contabilidad/centros-costo", icon: IconTargetArrow, cap: "contabilidad" },
      { id: "con-presupuestos", label: "Presupuestos", href: "/contabilidad/presupuestos", icon: IconChartPie, cap: "contabilidad" },
      { id: "con-estados", label: "Estados financieros", href: "/contabilidad/estados-financieros", icon: IconFileReport, cap: "contabilidad" },
    ],
  },
  {
    id: "compras",
    label: "Compras",
    num: "09",
    color: "#F76707",
    icon: IconTruck,
    subs: [
      { id: "com-proveedores", label: "Proveedores", href: "/compras/proveedores", icon: IconBuildingStore, cap: "compras" },
      { id: "com-requisiciones", label: "Requisiciones", href: "/compras/requisiciones", icon: IconClipboardList, cap: "compras" },
      { id: "com-rfq", label: "RFQ / Cotizaciones", href: "/compras/cotizaciones", icon: IconFileInvoice, cap: "compras" },
      { id: "com-ordenes", label: "Órdenes de compra", href: "/compras/ordenes", icon: IconShoppingCart, cap: "compras" },
      { id: "com-recepciones", label: "Recepciones", href: "/compras/recepciones", icon: IconPackageImport, cap: "compras" },
      { id: "com-facturas", label: "Facturas de proveedor", href: "/compras/facturas", icon: IconReceipt, cap: "compras" },
      { id: "com-evaluacion", label: "Evaluación", href: "/compras/evaluacion", icon: IconStar, cap: "compras" },
    ],
  },
  {
    id: "inventario",
    label: "Inventario",
    num: "10",
    color: "#7950F2",
    icon: IconBuildingWarehouse,
    subs: [
      { id: "inv-existencias", label: "Existencias", href: "/inventario/existencias", icon: IconPackage, cap: "inventario" },
      { id: "inv-movimientos", label: "Movimientos", href: "/inventario/movimientos", icon: IconTransfer, cap: "inventario" },
      { id: "inv-valorizacion", label: "Valorización y kardex", href: "/inventario/valorizacion", icon: IconCoin, cap: "inventario" },
      { id: "inv-lotes", label: "Lotes y series", href: "/inventario/lotes", icon: IconBarcode, cap: "inventario" },
      { id: "inv-transferencias", label: "Transferencias", href: "/inventario/transferencias", icon: IconArrowsExchange, cap: "inventario" },
      { id: "inv-bodegas", label: "Bodegas", href: "/inventario/bodegas", icon: IconBuildingWarehouse, cap: "inventario" },
      { id: "inv-arriendos", label: "Activos en arriendo", href: "/inventario/arriendos", icon: IconKey, cap: "arriendos" },
    ],
  },
  {
    id: "produccion",
    label: "Producción",
    num: "11",
    color: "#4263EB",
    icon: IconBuildingFactory,
    subs: [
      { id: "pro-ordenes", label: "Órdenes de producción", href: "/produccion/ordenes", icon: IconClipboardCheck, cap: "produccion" },
      { id: "pro-bom", label: "BOM", href: "/produccion/bom", icon: IconSitemap, cap: "produccion" },
      { id: "pro-mrp", label: "MRP", href: "/produccion/mrp", icon: IconCalendarTime, cap: "produccion" },
      { id: "pro-centros", label: "Centros de trabajo", href: "/produccion/centros-trabajo", icon: IconTools, cap: "produccion" },
      { id: "pro-calidad", label: "Control de calidad", href: "/produccion/calidad", icon: IconCircleCheck, cap: "produccion" },
    ],
  },
  {
    id: "activos",
    label: "Activos fijos",
    num: "12",
    color: "#1098AD",
    icon: IconBuildingSkyscraper,
    subs: [
      { id: "act-registro", label: "Registro", href: "/activos/registro", icon: IconClipboardList, cap: "activos_fijos" },
      { id: "act-depreciacion", label: "Depreciación", href: "/activos/depreciacion", icon: IconTrendingDown, cap: "activos_fijos" },
      { id: "act-mantenciones", label: "Mantenciones", href: "/activos/mantenciones", icon: IconTool, cap: "activos_fijos" },
      { id: "act-bajas", label: "Bajas", href: "/activos/bajas", icon: IconTrash, cap: "activos_fijos" },
    ],
  },
  {
    id: "rrhh",
    label: "Personas",
    num: "13",
    color: "#BE4BDB",
    icon: IconUsersGroup,
    subs: [
      { id: "rh-empleados", label: "Empleados", href: "/rrhh/empleados", icon: IconUsers, cap: "rrhh" },
      { id: "rh-contratos", label: "Contratos", href: "/rrhh/contratos", icon: IconFileText, cap: "rrhh" },
      { id: "rh-asistencia", label: "Asistencia", href: "/rrhh/asistencia", icon: IconClockCheck, cap: "rrhh" },
      { id: "rh-vacaciones", label: "Vacaciones", href: "/rrhh/vacaciones", icon: IconBeach, cap: "rrhh" },
      { id: "rh-liquidaciones", label: "Liquidaciones", href: "/rrhh/liquidaciones", icon: IconReceipt2, cap: "rrhh" },
      { id: "rh-remuneraciones", label: "Remuneraciones", href: "/rrhh/remuneraciones", icon: IconCoin, cap: "rrhh" },
      { id: "rh-reclutamiento", label: "Reclutamiento", href: "/rrhh/reclutamiento", icon: IconUserPlus, cap: "rrhh" },
      { id: "rh-desempeno", label: "Desempeño", href: "/rrhh/desempeno", icon: IconChartBar, cap: "rrhh" },
    ],
  },
  {
    id: "proyectos",
    label: "Proyectos",
    num: "14",
    color: "#66A80F",
    icon: IconBriefcase,
    subs: [
      { id: "prj-planificacion", label: "Planificación e hitos", href: "/proyectos/planificacion", icon: IconLayoutKanban, cap: "proyectos" },
      { id: "prj-horas", label: "Registro de horas", href: "/proyectos/horas", icon: IconClock, cap: "proyectos" },
      { id: "prj-presupuesto", label: "Presupuesto vs real", href: "/proyectos/presupuesto", icon: IconChartBar, cap: "proyectos" },
      { id: "prj-rentabilidad", label: "Rentabilidad", href: "/proyectos/rentabilidad", icon: IconTrendingUp, cap: "proyectos" },
    ],
  },
  {
    id: "documentos",
    label: "Documentos",
    num: "15",
    color: "#868E96",
    icon: IconFolder,
    subs: [
      { id: "doc-archivos", label: "Archivos", href: "/documentos/archivos", icon: IconFiles },
      { id: "doc-contratos", label: "Contratos", href: "/documentos/contratos", icon: IconFileText, cap: "contratos" },
      { id: "doc-consentimientos", label: "Consentimientos firmados", href: "/documentos/consentimientos", icon: IconSignature, cap: "consentimientos" },
      { id: "doc-tributarios", label: "Documentos tributarios", href: "/documentos/tributarios", icon: IconReceipt, cap: "facturacion" },
      { id: "doc-expedientes", label: "Expedientes y casos", href: "/documentos/expedientes", icon: IconFolderOpen, cap: "expedientes" },
    ],
  },
  {
    id: "contenido",
    label: "Contenido",
    num: "16",
    color: "#E64980",
    icon: IconSpeakerphone,
    subs: [
      { id: "cnt-campanas", label: "Campañas", href: "/contenido/campanas", icon: IconSpeakerphone, cap: "campanas" },
      { id: "cnt-medios", label: "Biblioteca de medios", href: "/contenido/medios", icon: IconPhoto },
      { id: "cnt-vitrina", label: "Catálogo público", href: "/contenido/vitrina", icon: IconWorld, cap: "catalogo" },
      { id: "cnt-fidelizacion", label: "Programa de fidelización", href: "/contenido/fidelizacion", icon: IconHeart, cap: "fidelizacion" },
    ],
  },
  {
    id: "cuenta",
    label: "Cuenta",
    num: "17",
    color: "#4C6EF5",
    icon: IconSettings,
    subs: [
      { id: "cta-perfil", label: "Perfil del negocio", href: "/cuenta/perfil", icon: IconBuildingStore },
      { id: "cta-equipo", label: "Equipo y permisos", href: "/cuenta/equipo", icon: IconUsersGroup },
      { id: "cta-multiempresa", label: "Multi-empresa", href: "/cuenta/multiempresa", icon: IconBuildingSkyscraper },
      { id: "cta-monedas", label: "Monedas", href: "/cuenta/monedas", icon: IconCurrencyDollar },
      { id: "cta-modulos", label: "Capacidades y módulos", href: "/cuenta/modulos", icon: IconPuzzle },
      { id: "cta-integraciones", label: "Integraciones", href: "/cuenta/integraciones", icon: IconPlugConnected },
      { id: "cta-facturacion", label: "Facturación del servicio", href: "/cuenta/facturacion", icon: IconCreditCard },
    ],
  },
];

/**
 * Sub visible ⟺ (sin cap o cap activa) y no deduplicada.
 * Dedup recurso/mesas: si el rubro tiene cap `mesas`, oculta `agenda-recursos` (la Agenda de
 * recursos duplicaría las Mesas del salón). Los rubros SIN `mesas` ocultan `ped-comandas` y
 * `ped-mesas` de forma natural (ambos gatean por cap `mesas`) y muestran `agenda-recursos`.
 */
function subVisible(sub: NavSubC, rubro: RubroDef): boolean {
  if (sub.cap && !tieneCapacidad(rubro.key, sub.cap)) return false;
  if (sub.id === "agenda-recursos" && tieneCapacidad(rubro.key, "mesas")) return false;
  return true;
}

/** Sidebar del rubro: subs visibles por categoría; categoría visible ⟺ ≥1 sub visible. */
export function construirSidebarCanonico(rubro: RubroDef): NavCatC[] {
  return NAV_CANONICO.map((cat) => ({
    ...cat,
    subs: cat.subs.filter((sub) => subVisible(sub, rubro)),
  })).filter((cat) => cat.subs.length > 0);
}

/** Label renderizado: restauranteLabel si RUBRO_DEFAULT; si no, rubroLabel?.(r) ?? label. */
export function navLabelCanonico(sub: NavSubC, rubro: RubroDef): string {
  if (rubro.key === RUBRO_DEFAULT) return sub.restauranteLabel ?? sub.label;
  return sub.rubroLabel?.(rubro) ?? sub.label;
}

/** Lista plana visible (CommandPalette/favoritos). Cada href es único ⇒ sin dedup por href. */
export function navItemsFlatCanonico(
  rubro: RubroDef,
): { sub: NavSubC; label: string; catLabel: string }[] {
  return construirSidebarCanonico(rubro).flatMap((cat) =>
    cat.subs.map((sub) => ({ sub, label: navLabelCanonico(sub, rubro), catLabel: cat.label })),
  );
}

/** Todos los `sub.id` canónicos (validación/dedupe de favoritos persistidos). */
const SUB_IDS_CANONICO = new Set(NAV_CANONICO.flatMap((cat) => cat.subs.map((sub) => sub.id)));

/**
 * Favoritos persistidos con ids legacy → `sub.id` canónico. Cubre los ids del nav viejo
 * `nav-config` (el shell corría con NAV_P2 OFF, así que esos son los que tienen los usuarios
 * reales) y los sub-ids del árbol P2 (por si alguien activó el flag). Los ids ya canónicos
 * pasan intactos; los huérfanos (ia, sudamerica-ia) y los retirados se descartan.
 */
export const LEGACY_FAV_TO_CANONICO: Record<string, string> = {
  // nav-config (ids = href sin "/")
  carta: "cat-productos",
  inventario: "inv-existencias",
  comandas: "ped-comandas",
  ventas: "ped-ordenes",
  mesas: "ped-mesas",
  reservaciones: "agenda-reservas",
  "entrenar-ia": "conv-ia",
  reportes: "din-reportes",
  leads: "contactos-directorio",
  billing: "cta-facturacion",
  equipo: "cta-equipo",
  configuracion: "cta-perfil",
  prospectos: "conv-bandeja",
  // sub-ids del árbol P2
  productos: "cat-productos",
  existencias: "inv-existencias",
  "mesas-salon": "ped-mesas",
  ordenes: "ped-ordenes",
  "reservas-citas": "agenda-reservas",
  "respuestas-ia": "conv-ia",
  "reportes-financieros": "din-reportes",
  ingresos: "din-ingresos",
  directorio: "contactos-directorio",
  "bandeja-de-entrada": "conv-bandeja",
  "facturacion-servicio": "cta-facturacion",
  "equipo-permisos": "cta-equipo",
  "perfil-negocio": "cta-perfil",
  "capacidades-modulos": "cta-modulos",
  integraciones: "cta-integraciones",
};

/** Migra favoritos legacy→canónico: remapea ids viejos, descarta desconocidos y dedupea. */
export function remapFavoritosCanonico(ids: readonly string[]): string[] {
  const remapped = ids
    .map((id) => LEGACY_FAV_TO_CANONICO[id] ?? id)
    .filter((id) => SUB_IDS_CANONICO.has(id));
  return [...new Set(remapped)];
}
