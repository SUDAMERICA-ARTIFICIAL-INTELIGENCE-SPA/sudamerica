import { describe, expect, it } from "vitest";

import { ESTADO_STOCK_UI, estadoStock } from "./inventario";

describe("estadoStock (F3 inventario)", () => {
  it("returns sin_stock when stock is zero or negative", () => {
    expect(estadoStock(0, 5)).toBe("sin_stock");
    expect(estadoStock(-1, 0)).toBe("sin_stock");
  });

  it("returns bajo when stock is at or below the minimum", () => {
    expect(estadoStock(5, 5)).toBe("bajo");
    expect(estadoStock(2, 5)).toBe("bajo");
  });

  it("returns ok when stock is above the minimum", () => {
    expect(estadoStock(6, 5)).toBe("ok");
    expect(estadoStock(1, 0)).toBe("ok");
  });

  it("exposes UI metadata for every estado", () => {
    for (const estado of ["sin_stock", "bajo", "ok"] as const) {
      expect(ESTADO_STOCK_UI[estado].label.length).toBeGreaterThan(0);
      expect(ESTADO_STOCK_UI[estado].color.length).toBeGreaterThan(0);
    }
  });
});
