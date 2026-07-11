// Árbol de navegación P2 (Entidad/objeto) — SSOT de la arquitectura de información
// para 100+ rubros, gateado por CAPACIDAD (decisión Fase 0: taxonomía P2, 11 categorías).
//
// Fuente: artifact "Sidebar · 3 propuestas para 100+ rubros" (Propuesta 2), con 3
// adaptaciones al modelo de 22 capacidades documentadas en BACKLOG_capacidades_100rubros.md:
//  1. "Órdenes de compra" se gatea por `compras` (el artifact la dejaba bajo `inventario`).
//  2. Sub nueva "Producción y recetas" gateada por `produccion` (capacidad nueva ERP).
//  3. "Proyectos y trabajos" se ubica bajo Pedidos gateada por `proyectos` (P2 del artifact
//     no la ubicaba); "Comandas" se gatea por `mesas` (equivale al comandas_kds del modelo
//     viejo, que solo restaurante tenía — evita mostrar jerga gastronómica a retail).
//
// Regla de visibilidad (construirSidebar): una sub es visible si no tiene `cap` o si la
// capacidad está activa; una categoría es visible si le queda ≥1 sub visible. Las
// categorías `fija` siempre tienen subs sin `cap`, por lo que siempre quedan visibles.
//
// Este árbol es la IA objetivo; el Sidebar actual (lib/nav-config.ts) gatea RUTAS
// existentes y migra su gating módulo→capacidad en la Etapa B (F4).

import type { Capacidad } from "./capacidades";
import type { RubroDef } from "./rubros";

export interface NavSub {
  /** ID estable (kebab-case) para goldens, keys de lista y futuros hrefs. */
  id: string;
  label: string;
  /** Capacidad que habilita esta sub; si falta, siempre visible dentro de su categoría. */
  cap?: Capacidad;
  /** Vistas (nivel 3) — informativas; no se gatean individualmente. */
  vistas: readonly string[];
}

export interface NavCategoria {
  id: string;
  label: string;
  /** Numeración del artifact ("01".."11") — orden estable del árbol. */
  num: string;
  /** Presente para todos los rubros (sus subs base no llevan `cap`). */
  fija: boolean;
  subs: readonly NavSub[];
}

export const NAV_TREE_P2: readonly NavCategoria[] = [
  {
    id: "inicio",
    label: "Inicio",
    num: "01",
    fija: true,
    subs: [
      {
        id: "resumen",
        label: "Resumen",
        vistas: ["KPIs del día", "Actividad reciente", "Alertas y avisos"],
      },
      {
        id: "tareas-del-dia",
        label: "Tareas del día",
        vistas: ["Pendientes", "Vencidas", "Asignadas a mí"],
      },
      {
        id: "notificaciones",
        label: "Notificaciones",
        vistas: ["No leídas", "Menciones", "Del sistema"],
      },
      { id: "accesos-rapidos", label: "Accesos rápidos", vistas: [] },
    ],
  },
  {
    id: "contactos",
    label: "Contactos",
    num: "02",
    fija: true,
    subs: [
      { id: "directorio", label: "Directorio", vistas: ["Personas", "Empresas", "Inactivos"] },
      {
        id: "segmentos",
        label: "Segmentos",
        vistas: ["Etiquetas", "Listas dinámicas", "Importar / exportar"],
      },
      { id: "ficha-de-contacto", label: "Ficha de contacto", vistas: [] },
      {
        id: "expedientes",
        label: "Fichas (Expedientes)",
        cap: "expedientes",
        vistas: ["Historial", "Documentos adjuntos", "Notas y evolución"],
      },
      {
        id: "consentimientos",
        label: "Consentimientos",
        cap: "consentimientos",
        vistas: ["Plantillas", "Firmados", "Pendientes de firma"],
      },
    ],
  },
  {
    id: "conversaciones",
    label: "Conversaciones",
    num: "03",
    fija: true,
    subs: [
      {
        id: "bandeja-de-entrada",
        label: "Bandeja de entrada",
        vistas: ["Sin asignar", "Asignadas a mí", "Cerradas"],
      },
      { id: "canales", label: "Canales", vistas: ["WhatsApp", "Email", "Redes sociales"] },
      {
        id: "respuestas-ia",
        label: "Respuestas de la IA",
        vistas: ["Por aprobar", "Aprobadas", "Rechazadas"],
      },
      { id: "plantillas", label: "Plantillas y respuestas rápidas", vistas: [] },
      {
        id: "tickets",
        label: "Tickets (Soporte)",
        cap: "soporte",
        vistas: ["Abiertos", "En espera", "Vencen SLA"],
      },
    ],
  },
  {
    id: "catalogo",
    label: "Catálogo",
    num: "04",
    fija: false,
    subs: [
      {
        id: "productos",
        label: "Productos",
        cap: "catalogo",
        vistas: ["Activos", "Agotados", "Borradores"],
      },
      {
        id: "servicios",
        label: "Servicios",
        cap: "catalogo",
        vistas: ["Por profesional", "Duración y precio", "Paquetes"],
      },
      {
        id: "variantes-precios",
        label: "Variantes y precios",
        cap: "catalogo",
        vistas: ["Tallas y colores", "Listas de precio", "Descuentos"],
      },
      {
        id: "cotizaciones",
        label: "Cotizaciones (Presupuestos)",
        cap: "cotizador",
        vistas: ["Borradores", "Enviadas", "Aprobadas"],
      },
      {
        id: "planes-membresias",
        label: "Planes y membresías",
        cap: "suscripciones",
        vistas: ["Planes activos", "Suscriptores", "Cobros recurrentes"],
      },
      {
        id: "cursos-programas",
        label: "Cursos y programas",
        cap: "cursos",
        vistas: ["Programas", "Clases", "Inscripciones"],
      },
    ],
  },
  {
    id: "agenda",
    label: "Agenda",
    num: "05",
    fija: false,
    subs: [
      {
        id: "calendario",
        label: "Calendario",
        cap: "agenda",
        vistas: ["Día", "Semana", "Por recurso"],
      },
      {
        id: "reservas-citas",
        label: "Reservas y citas",
        cap: "agenda",
        vistas: ["Confirmadas", "Pendientes", "Canceladas"],
      },
      {
        id: "disponibilidad",
        label: "Disponibilidad",
        cap: "agenda",
        vistas: ["Horarios", "Bloqueos", "Feriados"],
      },
      {
        id: "recursos-profesionales",
        label: "Recursos y profesionales",
        cap: "agenda",
        vistas: ["Personas", "Salas y equipos", "Asignación"],
      },
      {
        id: "visitas-terreno",
        label: "Visitas en terreno",
        cap: "terreno",
        vistas: ["Rutas del día", "Técnicos", "Check-in / check-out"],
      },
      {
        id: "disponibilidad-activos",
        label: "Disponibilidad de activos",
        cap: "arriendos",
        vistas: [],
      },
    ],
  },
  {
    id: "pedidos",
    label: "Pedidos",
    num: "06",
    fija: false,
    subs: [
      {
        id: "ordenes",
        label: "Órdenes",
        cap: "pedidos",
        vistas: ["Nuevas", "En preparación", "Listas"],
      },
      {
        id: "comandas",
        label: "Comandas",
        cap: "mesas",
        vistas: ["En cocina", "Por mesa", "Historial"],
      },
      {
        id: "mesas-salon",
        label: "Mesas y salón",
        cap: "mesas",
        vistas: ["Mapa de mesas", "Aforo", "Reservas de mesa"],
      },
      {
        id: "entregas",
        label: "Entregas",
        cap: "delivery",
        vistas: ["Por despachar", "En ruta", "Entregadas"],
      },
      {
        id: "proyectos-trabajos",
        label: "Proyectos y trabajos",
        cap: "proyectos",
        vistas: ["Por fase", "Hitos", "Avance"],
      },
      { id: "devoluciones", label: "Devoluciones", cap: "pedidos", vistas: [] },
    ],
  },
  {
    id: "dinero",
    label: "Dinero",
    num: "07",
    fija: true,
    subs: [
      { id: "ingresos", label: "Ingresos", vistas: ["Del día", "Del mes", "Por canal"] },
      {
        id: "cobros-pagos",
        label: "Cobros y pagos",
        cap: "pagos",
        vistas: ["Links de pago", "Punto de venta (POS)", "Transacciones"],
      },
      {
        id: "facturacion",
        label: "Facturación",
        cap: "facturacion",
        vistas: ["Boletas", "Facturas / DTE", "Notas de crédito"],
      },
      {
        id: "suscripciones-recurrencia",
        label: "Suscripciones y recurrencia",
        cap: "suscripciones",
        vistas: ["Cobros programados", "Fallidos", "Cancelaciones"],
      },
      {
        id: "reportes-financieros",
        label: "Reportes financieros",
        vistas: ["Ventas", "Impuestos", "Exportar contable"],
      },
    ],
  },
  {
    id: "inventario",
    label: "Inventario",
    num: "08",
    fija: false,
    subs: [
      {
        id: "existencias",
        label: "Existencias",
        cap: "inventario",
        vistas: ["Por bodega", "Stock bajo", "Sin movimiento"],
      },
      {
        id: "movimientos",
        label: "Movimientos",
        cap: "inventario",
        vistas: ["Entradas", "Salidas", "Ajustes"],
      },
      { id: "bodegas", label: "Bodegas y ubicaciones", cap: "inventario", vistas: [] },
      {
        id: "ordenes-compra",
        label: "Órdenes de compra",
        cap: "compras",
        vistas: ["Borradores", "Enviadas", "Recibidas"],
      },
      {
        id: "produccion-recetas",
        label: "Producción y recetas",
        cap: "produccion",
        vistas: ["Recetas / BOM", "Órdenes de producción", "Costeo"],
      },
      {
        id: "activos-arriendo",
        label: "Activos en arriendo",
        cap: "arriendos",
        vistas: ["Disponibles", "Arrendados", "En mantención"],
      },
    ],
  },
  {
    id: "documentos",
    label: "Documentos",
    num: "09",
    fija: true,
    subs: [
      { id: "archivos", label: "Archivos", vistas: ["Recientes", "Compartidos", "Papelera"] },
      {
        id: "contratos",
        label: "Contratos",
        cap: "contratos",
        vistas: ["Borradores", "Por firmar", "Vigentes"],
      },
      {
        id: "consentimientos-firmados",
        label: "Consentimientos firmados",
        cap: "consentimientos",
        vistas: [],
      },
      {
        id: "documentos-tributarios",
        label: "Documentos tributarios",
        cap: "facturacion",
        vistas: ["Emitidos", "Anulados", "Por emitir"],
      },
      {
        id: "expedientes-casos",
        label: "Expedientes y casos",
        cap: "expedientes",
        vistas: ["Abiertos", "En curso", "Archivados"],
      },
    ],
  },
  {
    id: "contenido",
    label: "Contenido",
    num: "10",
    fija: true,
    subs: [
      {
        id: "campanas",
        label: "Campañas",
        cap: "campanas",
        vistas: ["Borradores", "Programadas", "Enviadas"],
      },
      { id: "biblioteca-medios", label: "Biblioteca de medios", vistas: [] },
      {
        id: "catalogo-publico",
        label: "Catálogo público",
        cap: "catalogo",
        vistas: ["Vitrina", "Enlaces para compartir", "Destacados"],
      },
      {
        id: "programa-fidelizacion",
        label: "Programa de fidelización",
        cap: "fidelizacion",
        vistas: ["Reglas de puntos", "Recompensas", "Miembros"],
      },
    ],
  },
  {
    id: "cuenta",
    label: "Cuenta",
    num: "11",
    fija: true,
    subs: [
      {
        id: "perfil-negocio",
        label: "Perfil del negocio",
        vistas: ["Datos", "Horarios de atención", "Sucursales"],
      },
      {
        id: "equipo-permisos",
        label: "Equipo y permisos",
        vistas: ["Usuarios", "Roles", "Invitaciones"],
      },
      {
        id: "capacidades-modulos",
        label: "Capacidades y módulos",
        vistas: ["Activas", "Disponibles", "Del plan"],
      },
      { id: "integraciones", label: "Integraciones", vistas: ["Canales", "Pagos", "Webhooks"] },
      { id: "facturacion-servicio", label: "Facturación del servicio", vistas: [] },
    ],
  },
];

/**
 * Filtra el árbol P2 según las capacidades activas del tenant.
 * Sub visible ⟺ sin `cap` o `cap` activa; categoría visible ⟺ ≥1 sub visible.
 */
export function construirSidebar(capacidades: readonly Capacidad[]): NavCategoria[] {
  const activas = new Set(capacidades);
  const visibles: NavCategoria[] = [];
  for (const categoria of NAV_TREE_P2) {
    const subs = categoria.subs.filter((sub) => !sub.cap || activas.has(sub.cap));
    if (subs.length > 0) {
      visibles.push({ ...categoria, subs });
    }
  }
  return visibles;
}

/** Conveniencia: árbol filtrado desde la definición de rubro (tenant.config → rubro → capacidades). */
export function construirSidebarParaRubro(rubro: RubroDef): NavCategoria[] {
  return construirSidebar(rubro.capacidades);
}
