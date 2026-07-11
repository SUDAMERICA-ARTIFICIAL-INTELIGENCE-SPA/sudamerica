// Operativa por rubro (F4/F5 multi-rubro): estados de orden y roles de equipo.
// Espejo de shared/rubros/operativa.py (backend). Mantener ambos en sync.
// Estados/roles NO se configuran a mano por rubro: se derivan de sus módulos
// (comandas_kds ⇒ fase de cocina; recurso ⇒ rol de sala). Restaurante reproduce
// EXACTAMENTE COMANDA_TRANSITIONS de enums.ts (byte-idéntico; test de
// sincronización en operativa.test.ts).

import { UserRole } from "./enums";
import { getRubroDef } from "./rubros";

export type EstadoOrden =
  | "PENDIENTE"
  | "EN_COCINA"
  | "EN_PROCESO"
  | "LISTO"
  | "ENTREGADO"
  | "CANCELADO";

type Transiciones = Readonly<Record<string, readonly EstadoOrden[]>>;

const TRANSICIONES_COCINA: Transiciones = {
  PENDIENTE: ["EN_COCINA", "CANCELADO"],
  EN_COCINA: ["LISTO", "CANCELADO"],
  LISTO: ["ENTREGADO", "CANCELADO"],
  ENTREGADO: [],
  CANCELADO: [],
};

// Sin cocina la preparación es opcional: PENDIENTE puede saltar directo a LISTO.
const TRANSICIONES_GENERICAS: Transiciones = {
  PENDIENTE: ["EN_PROCESO", "LISTO", "CANCELADO"],
  EN_PROCESO: ["LISTO", "CANCELADO"],
  LISTO: ["ENTREGADO", "CANCELADO"],
  ENTREGADO: [],
  CANCELADO: [],
};

/** FSM de estados de la orden para el rubro (restaurante = FSM clásico); fail-safe. */
export function transicionesOrden(rubroKey: string): Transiciones {
  if (getRubroDef(rubroKey).capacidades.includes("mesas")) {
    return TRANSICIONES_COCINA;
  }
  return TRANSICIONES_GENERICAS;
}

/** Estados válidos de la orden para el rubro. */
export function estadosOrden(rubroKey: string): readonly EstadoOrden[] {
  return Object.keys(transicionesOrden(rubroKey)) as EstadoOrden[];
}

/** ¿La transición `actual → objetivo` es válida en el FSM del rubro? */
export function puedeTransicionar(rubroKey: string, actual: string, objetivo: string): boolean {
  return (transicionesOrden(rubroKey)[actual] ?? []).some((estado) => estado === objetivo);
}

// ── Roles de equipo por rubro (superset ya existente en UserRole) ─────────────

const ROLES_BASE: readonly UserRole[] = [
  UserRole.SUPERADMIN,
  UserRole.ADMIN,
  UserRole.GERENTE,
  UserRole.CAJA,
  UserRole.PERSONAL,
  UserRole.VIEWER,
];
const ROL_SALA = UserRole.MESERO; // requiere flag recurso (atención en sala/recurso físico)
const ROL_COCINA = UserRole.COCINA; // requiere capacidad mesas (cocina/salón)

/** Roles aplicables al rubro; restaurante conserva el set completo actual. */
export function rolesEquipo(rubroKey: string): readonly UserRole[] {
  const def = getRubroDef(rubroKey);
  const roles: UserRole[] = [...ROLES_BASE];
  if (def.recurso) {
    roles.push(ROL_SALA);
  }
  if (def.capacidades.includes("mesas")) {
    roles.push(ROL_COCINA);
  }
  return roles;
}

// ── Recurso físico reservable (F5, fase expand) ───────────────────────────────

/** Tipo del recurso reservable del rubro (columna `mesas.tipo`): mesa/silla/… */
export function tipoRecursoDefault(rubroKey: string): string {
  return getRubroDef(rubroKey).labels.recurso.toLowerCase();
}
