// Catálogo de capacidades (ERP+CRM) — espejo de shared/rubros/capacidades.py (backend).
// Mantener ambos en sync. 22 capacidades = 20 del artifact "Sidebar · 3 propuestas para
// 100+ rubros" + 2 nuevas ERP (compras, produccion) decididas en Fase 0.
// El campo `capacidades` STORED por rubro (lib/rubros.ts) es el canónico (curado,
// Fase 2). La derivación §3 se retiró junto con `modulos` en la Etapa B; los modos
// de dato (recurso/variantes/precioMedida) viven como flags del RubroDef.

// Orden canónico (CAP_ORDER): las listas `capacidades` de cada rubro se guardan en
// este orden en AMBOS SSOT (Py y TS) para que el espejo sea determinista.
export const CAPACIDADES = [
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
] as const;

export type Capacidad = (typeof CAPACIDADES)[number];

export interface CapacidadMeta {
  slug: Capacidad;
  label: string;
  descripcion: string;
  eje: string;
}

export const CAPACIDADES_META: Record<Capacidad, CapacidadMeta> = {
  catalogo: {
    slug: "catalogo",
    label: "Catálogo",
    descripcion: "Productos/servicios con precios, variantes y fotos.",
    eje: "venta",
  },
  agenda: {
    slug: "agenda",
    label: "Agenda",
    descripcion: "Reserva de horas, citas y turnos con recursos/profesionales.",
    eje: "servicio",
  },
  cotizador: {
    slug: "cotizador",
    label: "Cotizador",
    descripcion: "Presupuestos configurables y su aprobación.",
    eje: "erp",
  },
  pedidos: {
    slug: "pedidos",
    label: "Pedidos",
    descripcion: "Órdenes/comandas/órdenes de servicio y su preparación.",
    eje: "operacion",
  },
  pagos: {
    slug: "pagos",
    label: "Pagos",
    descripcion: "Cobro con links, tarjetas y POS. Incluye caja: apertura/arqueo/cierre por turno.",
    eje: "dinero",
  },
  delivery: {
    slug: "delivery",
    label: "Delivery",
    descripcion: "Despacho, reparto y seguimiento de entregas.",
    eje: "logistica",
  },
  suscripciones: {
    slug: "suscripciones",
    label: "Suscripciones",
    descripcion: "Planes recurrentes, membresías, cobros automáticos.",
    eje: "dinero",
  },
  soporte: {
    slug: "soporte",
    label: "Soporte",
    descripcion: "Tickets, casos, mesa de ayuda con SLA. Incluye garantías/RMA post-venta.",
    eje: "crm",
  },
  proyectos: {
    slug: "proyectos",
    label: "Proyectos",
    descripcion: "Trabajos por fases, hitos y avance (incluye obras).",
    eje: "erp",
  },
  inventario: {
    slug: "inventario",
    label: "Inventario",
    descripcion: "Stock, bodegas y movimientos de existencias (producto terminado).",
    eje: "erp",
  },
  compras: {
    slug: "compras",
    label: "Compras",
    descripcion: "Órdenes de compra, proveedores, recepción de mercadería y cuentas por pagar.",
    eje: "erp",
  },
  produccion: {
    slug: "produccion",
    label: "Producción",
    descripcion: "Recetas/BOM, consumo de insumos, órdenes de producción y costeo.",
    eje: "erp",
  },
  expedientes: {
    slug: "expedientes",
    label: "Expedientes",
    descripcion: "Fichas e historial de cliente/paciente/caso.",
    eje: "crm_salud",
  },
  contratos: {
    slug: "contratos",
    label: "Contratos",
    descripcion: "Documentos, firma y control de vigencias.",
    eje: "erp_legal",
  },
  cursos: {
    slug: "cursos",
    label: "Cursos",
    descripcion: "Programas, clases, inscripción y asistencia.",
    eje: "educacion",
  },
  arriendos: {
    slug: "arriendos",
    label: "Arriendos",
    descripcion: "Alquiler de activos y calendario de disponibilidad.",
    eje: "erp",
  },
  facturacion: {
    slug: "facturacion",
    label: "Facturación",
    descripcion:
      "Documentos tributarios (boleta/factura/DTE, notas de crédito). Incluye cuentas por cobrar/crédito B2B y facturación previsional salud (bono/reembolso).",
    eje: "erp",
  },
  fidelizacion: {
    slug: "fidelizacion",
    label: "Fidelización",
    descripcion: "Puntos, sellos, niveles y recompensas.",
    eje: "crm",
  },
  campanas: {
    slug: "campanas",
    label: "Campañas",
    descripcion: "Difusión y mensajería masiva a segmentos.",
    eje: "crm",
  },
  terreno: {
    slug: "terreno",
    label: "Terreno",
    descripcion: "Visitas, rutas y técnicos en terreno.",
    eje: "erp",
  },
  mesas: {
    slug: "mesas",
    label: "Mesas",
    descripcion: "Gestión de mesas, aforo y sala.",
    eje: "gastronomia",
  },
  consentimientos: {
    slug: "consentimientos",
    label: "Consentimientos",
    descripcion: "Formularios y consentimientos firmados.",
    eje: "salud_legal",
  },
};
