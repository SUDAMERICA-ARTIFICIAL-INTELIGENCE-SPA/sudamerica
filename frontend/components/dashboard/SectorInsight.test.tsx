import { type RubroKey, getRubroDef } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { SectorInsight } from "./SectorInsight";

// jsdom no trae matchMedia/ResizeObserver (los usa Mantine).
beforeAll(() => {
  window.matchMedia ??= ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as typeof window.matchMedia;
  window.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

let rubroKey: RubroKey = "restaurante";

vi.mock("@/hooks/useRubroLabels", () => ({
  useRubroLabels: () => ({ ...getRubroDef(rubroKey), isLoading: false }),
}));

function renderInsight(key: RubroKey) {
  rubroKey = key;
  return render(
    <MantineProvider>
      <SectorInsight />
    </MantineProvider>,
  );
}

describe("SectorInsight (rubro-aware)", () => {
  it("muestra el KPI clave del sector gastronomía para restaurante", () => {
    renderInsight("restaurante");
    expect(screen.getByText("Recurrencia de Compra")).toBeInTheDocument();
    expect(screen.getByText("KPI clave de tu sector")).toBeInTheDocument();
  });

  it("muestra el KPI clave del sector salud_estética para peluquería", () => {
    renderInsight("peluqueria");
    expect(screen.getByText("Tasa No-Show")).toBeInTheDocument();
    // No filtra strings de gastronomía en un tenant no-restaurante.
    expect(screen.queryByText("Recurrencia de Compra")).not.toBeInTheDocument();
  });
});
