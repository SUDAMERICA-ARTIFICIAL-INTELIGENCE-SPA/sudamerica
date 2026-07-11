export enum LeadEstado {
  NUEVO = "NUEVO",
  CONTACTADO = "CONTACTADO",
  EN_PROCESO = "EN_PROCESO",
  CONVERTIDO = "CONVERTIDO",
  DESCARTADO = "DESCARTADO",
}

export enum LeadCanal {
  WHATSAPP = "WHATSAPP",
  INSTAGRAM = "INSTAGRAM",
  FACEBOOK = "FACEBOOK",
  WEB = "WEB",
  TELEFONO = "TELEFONO",
  EMAIL = "EMAIL",
  REFERIDO = "REFERIDO",
}

export enum UserRole {
  SUPERADMIN = "SUPERADMIN",
  ADMIN = "ADMIN",
  GERENTE = "GERENTE",
  MESERO = "MESERO",
  COCINA = "COCINA",
  CAJA = "CAJA",
  PERSONAL = "PERSONAL",
  ASESOR = "ASESOR", // deprecated
  VIEWER = "VIEWER",
}

export const USER_ROLE_LABELS: Record<string, string> = {
  SUPERADMIN: "Super Admin",
  ADMIN: "Administrador",
  GERENTE: "Gerente Sucursal",
  MESERO: "Mesero",
  COCINA: "Cocina",
  CAJA: "Caja",
  PERSONAL: "Personal",
  ASESOR: "Personal",
  VIEWER: "Viewer",
};

export const USER_ROLE_COLORS: Record<string, string> = {
  SUPERADMIN: "red",
  ADMIN: "indigo",
  GERENTE: "violet",
  MESERO: "teal",
  COCINA: "orange",
  CAJA: "cyan",
  PERSONAL: "teal",
  ASESOR: "teal",
  VIEWER: "gray",
};

export enum TenantPlan {
  ESTANDAR = "ESTANDAR",
  PLUS = "PLUS",
  PRO = "PRO",
  FREE = "FREE", // deprecated
}

export enum RevisionAccion {
  APROBAR = "APROBAR",
  EDITAR = "EDITAR",
  RECHAZAR = "RECHAZAR",
}

export enum SubAgenteType {
  RAG = "RAG",
  COTIZADOR = "COTIZADOR",
  SEGUIMIENTO = "SEGUIMIENTO",
  FAQ = "FAQ",
}

export enum SmartAlertType {
  HOT_LEAD = "hot_lead",
  STALLED_DEAL = "stalled_deal",
  CHURN_RISK = "churn_risk",
  ANOMALY_DETECTED = "anomaly_detected",
  NO_SHOW_RISK = "no_show_risk",
}

// Valid lead FSM transitions
export const LEAD_TRANSITIONS: Record<LeadEstado, readonly LeadEstado[]> = {
  [LeadEstado.NUEVO]: [LeadEstado.CONTACTADO, LeadEstado.DESCARTADO],
  [LeadEstado.CONTACTADO]: [LeadEstado.EN_PROCESO, LeadEstado.DESCARTADO],
  [LeadEstado.EN_PROCESO]: [LeadEstado.CONVERTIDO, LeadEstado.DESCARTADO],
  [LeadEstado.CONVERTIDO]: [],
  [LeadEstado.DESCARTADO]: [],
} as const;

export function canTransition(from: LeadEstado, to: LeadEstado): boolean {
  return LEAD_TRANSITIONS[from].includes(to);
}

export enum InteractionTipo {
  LLAMADA = "LLAMADA",
  NOTA = "NOTA",
  EMAIL = "EMAIL",
  WHATSAPP = "WHATSAPP",
  REUNION = "REUNION",
}

export enum CalendarEventTipo {
  LLAMADA = "LLAMADA",
  REUNION = "REUNION",
  SEGUIMIENTO = "SEGUIMIENTO",
  DEMO = "DEMO",
}

export enum QuoteEstado {
  BORRADOR = "BORRADOR",
  ENVIADA = "ENVIADA",
  ACEPTADA = "ACEPTADA",
  RECHAZADA = "RECHAZADA",
}

// ─── Sudamérica AI Resto (Gastronomy) ───

export enum TipoEntrega {
  MESA = "MESA",
  DELIVERY = "DELIVERY",
  RETIRO = "RETIRO",
}

export enum CanalOrigen {
  WHATSAPP = "WHATSAPP",
  WEB = "WEB",
  PRESENCIAL = "PRESENCIAL",
}

export enum ComandaEstado {
  PENDIENTE = "PENDIENTE",
  EN_COCINA = "EN_COCINA",
  /** F4 multi-rubro: fase de preparación genérica (rubros sin cocina). */
  EN_PROCESO = "EN_PROCESO",
  LISTO = "LISTO",
  ENTREGADO = "ENTREGADO",
  CANCELADO = "CANCELADO",
}

export const COMANDA_TRANSITIONS: Record<ComandaEstado, readonly ComandaEstado[]> = {
  [ComandaEstado.PENDIENTE]: [ComandaEstado.EN_COCINA, ComandaEstado.CANCELADO],
  [ComandaEstado.EN_COCINA]: [ComandaEstado.LISTO, ComandaEstado.CANCELADO],
  [ComandaEstado.EN_PROCESO]: [ComandaEstado.LISTO, ComandaEstado.CANCELADO],
  [ComandaEstado.LISTO]: [ComandaEstado.ENTREGADO, ComandaEstado.CANCELADO],
  [ComandaEstado.ENTREGADO]: [],
  [ComandaEstado.CANCELADO]: [],
} as const;

export enum ModifierGroupTipo {
  SINGLE_SELECT = "SINGLE_SELECT",
  MULTI_SELECT = "MULTI_SELECT",
}

export enum ClienteEstado {
  NUEVO = "NUEVO",
  OCASIONAL = "OCASIONAL",
  FRECUENTE = "FRECUENTE",
  VIP = "VIP",
  INACTIVO = "INACTIVO",
}

export const CLIENTE_ESTADO_LABELS: Record<ClienteEstado, string> = {
  [ClienteEstado.NUEVO]: "Nuevo",
  [ClienteEstado.OCASIONAL]: "Ocasional",
  [ClienteEstado.FRECUENTE]: "Frecuente",
  [ClienteEstado.VIP]: "VIP",
  [ClienteEstado.INACTIVO]: "Inactivo",
};

export const CLIENTE_ESTADO_COLORS: Record<ClienteEstado, string> = {
  [ClienteEstado.NUEVO]: "blue",
  [ClienteEstado.OCASIONAL]: "cyan",
  [ClienteEstado.FRECUENTE]: "teal",
  [ClienteEstado.VIP]: "yellow",
  [ClienteEstado.INACTIVO]: "gray",
};
