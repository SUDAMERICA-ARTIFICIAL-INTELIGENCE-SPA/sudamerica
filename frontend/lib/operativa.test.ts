import { describe, expect, it } from "vitest";
import { COMANDA_TRANSITIONS, ComandaEstado, UserRole } from "./enums";
import {
  estadosOrden,
  puedeTransicionar,
  rolesEquipo,
  tipoRecursoDefault,
  transicionesOrden,
} from "./operativa";

// Espejo de shared/tests/test_operativa.py (backend). Mantener ambos en sync.

// ── Sincronización restaurante (byte-idéntico) ───────────────────────────────

describe("FSM restaurante sincronizado con enums.ts", () => {
  it("es exactamente COMANDA_TRANSITIONS sin el estado EN_PROCESO", () => {
    const { [ComandaEstado.EN_PROCESO]: _enProceso, ...clasico } = COMANDA_TRANSITIONS;
    expect(transicionesOrden("restaurante")).toEqual(clasico);
  });

  it("la fila EN_PROCESO del FSM genérico coincide con COMANDA_TRANSITIONS", () => {
    expect(transicionesOrden("ferreteria")[ComandaEstado.EN_PROCESO]).toEqual(
      COMANDA_TRANSITIONS[ComandaEstado.EN_PROCESO],
    );
  });

  it("restaurante no puede usar EN_PROCESO", () => {
    expect(puedeTransicionar("restaurante", "PENDIENTE", "EN_PROCESO")).toBe(false);
    expect(estadosOrden("restaurante")).not.toContain("EN_PROCESO");
  });

  it("roles de restaurante = set completo actual", () => {
    const roles = rolesEquipo("restaurante");
    for (const rol of [
      UserRole.MESERO,
      UserRole.COCINA,
      UserRole.CAJA,
      UserRole.GERENTE,
      UserRole.ADMIN,
    ]) {
      expect(roles).toContain(rol);
    }
  });
});

// ── FSM genérico (rubros sin cocina) ─────────────────────────────────────────

describe("FSM genérico", () => {
  it("ferreteria: preparación opcional, sin cocina", () => {
    expect(puedeTransicionar("ferreteria", "PENDIENTE", "EN_PROCESO")).toBe(true);
    expect(puedeTransicionar("ferreteria", "PENDIENTE", "LISTO")).toBe(true); // sin preparación
    expect(puedeTransicionar("ferreteria", "EN_PROCESO", "LISTO")).toBe(true);
    expect(puedeTransicionar("ferreteria", "LISTO", "ENTREGADO")).toBe(true);
    expect(puedeTransicionar("ferreteria", "PENDIENTE", "EN_COCINA")).toBe(false);
  });

  it("estados terminales no transicionan en ningún FSM", () => {
    for (const rubro of ["restaurante", "ferreteria", "peluqueria"]) {
      expect(puedeTransicionar(rubro, "ENTREGADO", "PENDIENTE")).toBe(false);
      expect(puedeTransicionar(rubro, "CANCELADO", "PENDIENTE")).toBe(false);
    }
  });

  it("todo estado no terminal permite cancelar", () => {
    for (const rubro of ["restaurante", "ferreteria"]) {
      for (const [estado, targets] of Object.entries(transicionesOrden(rubro))) {
        if (targets.length > 0) {
          expect(targets, `${rubro}:${estado}`).toContain("CANCELADO");
        }
      }
    }
  });

  it("estado desconocido no transiciona", () => {
    expect(puedeTransicionar("ferreteria", "INVENTADO", "LISTO")).toBe(false);
  });
});

// ── Roles derivados de módulos ───────────────────────────────────────────────

describe("rolesEquipo", () => {
  it("siempre es subconjunto de UserRole", () => {
    const validos = new Set<string>(Object.values(UserRole));
    for (const rubro of ["restaurante", "peluqueria", "ferreteria", "veterinaria"]) {
      for (const rol of rolesEquipo(rubro)) {
        expect(validos.has(rol)).toBe(true);
      }
    }
  });

  it("ferreteria sin roles de sala ni cocina", () => {
    const roles = rolesEquipo("ferreteria");
    expect(roles).not.toContain(UserRole.MESERO);
    expect(roles).not.toContain(UserRole.COCINA);
    expect(roles).toContain(UserRole.CAJA);
  });

  it("peluqueria con rol de sala, sin cocina", () => {
    const roles = rolesEquipo("peluqueria");
    expect(roles).toContain(UserRole.MESERO); // módulo recurso ON (silla)
    expect(roles).not.toContain(UserRole.COCINA);
  });
});

// ── Tipo de recurso (F5) ─────────────────────────────────────────────────────

describe("tipoRecursoDefault", () => {
  it("deriva del label RECURSO del rubro (fail-safe restaurante)", () => {
    expect(tipoRecursoDefault("restaurante")).toBe("mesa");
    expect(tipoRecursoDefault("peluqueria")).toBe("silla");
    expect(tipoRecursoDefault("desconocido")).toBe("mesa"); // fail-safe
  });
});
