import { describe, expect, it } from "vitest";
import {
  ComandaEstado,
  COMANDA_TRANSITIONS,
  LeadEstado,
  LEAD_TRANSITIONS,
  canTransition,
} from "./enums";

describe("canTransition", () => {
  it("allows NUEVO -> CONTACTADO", () => {
    expect(canTransition(LeadEstado.NUEVO, LeadEstado.CONTACTADO)).toBe(true);
  });

  it("allows NUEVO -> DESCARTADO", () => {
    expect(canTransition(LeadEstado.NUEVO, LeadEstado.DESCARTADO)).toBe(true);
  });

  it("rejects NUEVO -> CONVERTIDO (skip)", () => {
    expect(canTransition(LeadEstado.NUEVO, LeadEstado.CONVERTIDO)).toBe(false);
  });

  it("rejects NUEVO -> EN_PROCESO (skip)", () => {
    expect(canTransition(LeadEstado.NUEVO, LeadEstado.EN_PROCESO)).toBe(false);
  });

  it("allows CONTACTADO -> EN_PROCESO", () => {
    expect(canTransition(LeadEstado.CONTACTADO, LeadEstado.EN_PROCESO)).toBe(true);
  });

  it("allows CONTACTADO -> DESCARTADO", () => {
    expect(canTransition(LeadEstado.CONTACTADO, LeadEstado.DESCARTADO)).toBe(true);
  });

  it("allows EN_PROCESO -> CONVERTIDO", () => {
    expect(canTransition(LeadEstado.EN_PROCESO, LeadEstado.CONVERTIDO)).toBe(true);
  });

  it("allows EN_PROCESO -> DESCARTADO", () => {
    expect(canTransition(LeadEstado.EN_PROCESO, LeadEstado.DESCARTADO)).toBe(true);
  });

  it("rejects transitions from CONVERTIDO (terminal)", () => {
    expect(canTransition(LeadEstado.CONVERTIDO, LeadEstado.NUEVO)).toBe(false);
    expect(canTransition(LeadEstado.CONVERTIDO, LeadEstado.DESCARTADO)).toBe(false);
  });

  it("rejects transitions from DESCARTADO (terminal)", () => {
    expect(canTransition(LeadEstado.DESCARTADO, LeadEstado.NUEVO)).toBe(false);
    expect(canTransition(LeadEstado.DESCARTADO, LeadEstado.CONTACTADO)).toBe(false);
  });

  it("rejects backward transitions", () => {
    expect(canTransition(LeadEstado.EN_PROCESO, LeadEstado.NUEVO)).toBe(false);
    expect(canTransition(LeadEstado.CONTACTADO, LeadEstado.NUEVO)).toBe(false);
  });
});

describe("LEAD_TRANSITIONS", () => {
  it("covers all LeadEstado keys", () => {
    const allEstados = Object.values(LeadEstado);
    for (const estado of allEstados) {
      expect(LEAD_TRANSITIONS).toHaveProperty(estado);
    }
  });

  it("terminal states have empty arrays", () => {
    expect(LEAD_TRANSITIONS[LeadEstado.CONVERTIDO]).toEqual([]);
    expect(LEAD_TRANSITIONS[LeadEstado.DESCARTADO]).toEqual([]);
  });

  it("non-terminal states have at least one transition", () => {
    expect(LEAD_TRANSITIONS[LeadEstado.NUEVO].length).toBeGreaterThan(0);
    expect(LEAD_TRANSITIONS[LeadEstado.CONTACTADO].length).toBeGreaterThan(0);
    expect(LEAD_TRANSITIONS[LeadEstado.EN_PROCESO].length).toBeGreaterThan(0);
  });
});

describe("COMANDA_TRANSITIONS", () => {
  it("covers all ComandaEstado keys", () => {
    const allEstados = Object.values(ComandaEstado);
    for (const estado of allEstados) {
      expect(COMANDA_TRANSITIONS).toHaveProperty(estado);
    }
  });

  it("allows PENDIENTE -> EN_COCINA", () => {
    expect(COMANDA_TRANSITIONS[ComandaEstado.PENDIENTE]).toContain(ComandaEstado.EN_COCINA);
  });

  it("allows PENDIENTE -> CANCELADO", () => {
    expect(COMANDA_TRANSITIONS[ComandaEstado.PENDIENTE]).toContain(ComandaEstado.CANCELADO);
  });

  it("allows EN_COCINA -> LISTO", () => {
    expect(COMANDA_TRANSITIONS[ComandaEstado.EN_COCINA]).toContain(ComandaEstado.LISTO);
  });

  it("allows LISTO -> ENTREGADO", () => {
    expect(COMANDA_TRANSITIONS[ComandaEstado.LISTO]).toContain(ComandaEstado.ENTREGADO);
  });

  it("terminal states have empty arrays", () => {
    expect(COMANDA_TRANSITIONS[ComandaEstado.ENTREGADO]).toEqual([]);
    expect(COMANDA_TRANSITIONS[ComandaEstado.CANCELADO]).toEqual([]);
  });

  it("every non-terminal state allows CANCELADO", () => {
    const nonTerminal = [ComandaEstado.PENDIENTE, ComandaEstado.EN_COCINA, ComandaEstado.LISTO];
    for (const estado of nonTerminal) {
      expect(COMANDA_TRANSITIONS[estado]).toContain(ComandaEstado.CANCELADO);
    }
  });
});
