import { getVisibleNavItemsFlatP2 } from "@/lib/nav-p2";
import { getRubroDef } from "@/lib/rubros";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DEV_RUBRO_OVERRIDE_KEY, readDevRubroOverride, useRubroLabels } from "./useRubroLabels";

// Mock del tenant — el hook solo consume { data, isLoading } del query.
const mockTenant = {
  current: { config: { rubro: "restaurante" } as Record<string, unknown> | undefined },
};
vi.mock("@/hooks/useTenant", () => ({
  useTenant: () => ({ data: mockTenant.current, isLoading: false }),
}));

afterEach(() => {
  vi.unstubAllEnvs();
  window.localStorage.clear();
  mockTenant.current = { config: { rubro: "restaurante" } };
});

describe("readDevRubroOverride (gate por NEXT_PUBLIC_MOCK_AUTH)", () => {
  it("devuelve null con el flag OFF aunque haya override guardado", () => {
    // Arrange
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "");
    window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, "peluqueria");

    // Act + Assert
    expect(readDevRubroOverride()).toBeNull();
  });

  it("devuelve el override guardado con el flag ON", () => {
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "true");
    window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, "ferreteria");

    expect(readDevRubroOverride()).toBe("ferreteria");
  });

  it("devuelve null con el flag ON si no hay override guardado", () => {
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "true");

    expect(readDevRubroOverride()).toBeNull();
  });
});

describe("useRubroLabels con override dev", () => {
  it("el override dev gana sobre el rubro del tenant cuando el flag está ON", async () => {
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "true");
    window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, "peluqueria");

    const { result } = renderHook(() => useRubroLabels());

    await waitFor(() => {
      expect(result.current.key).toBe("peluqueria");
    });
  });

  it("resolveRubro manda cuando el flag está OFF, ignorando el localStorage", async () => {
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "");
    window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, "peluqueria");
    mockTenant.current = { config: { rubro: "ferreteria" } };

    const { result } = renderHook(() => useRubroLabels());

    await waitFor(() => {
      expect(result.current.key).toBe("ferreteria");
    });
  });

  it("un override inválido cae fail-safe al default (restaurante), no al rubro del tenant", async () => {
    vi.stubEnv("NEXT_PUBLIC_MOCK_AUTH", "true");
    window.localStorage.setItem(DEV_RUBRO_OVERRIDE_KEY, "rubro-inexistente");
    mockTenant.current = { config: { rubro: "peluqueria" } };

    const { result } = renderHook(() => useRubroLabels());

    await waitFor(() => {
      expect(result.current.key).toBe("restaurante");
    });
  });
});

describe("el label del nav P2 sigue al rubro activo (lo que verifica el switcher)", () => {
  const labelDe = (rubroKey: string, id: string) =>
    getVisibleNavItemsFlatP2(getRubroDef(rubroKey)).find((f) => f.item.id === id)?.label;

  it("catálogo se llama 'Carta & Menu' en restaurante y 'Productos' en peluquería", () => {
    expect(labelDe("restaurante", "productos")).toBe("Carta & Menu");
    expect(labelDe("peluqueria", "productos")).toBe("Productos");
  });
});
