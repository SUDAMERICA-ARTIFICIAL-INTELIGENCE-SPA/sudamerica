import { type RubroKey, getRubroDef } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { AIPerformanceHeader } from "./AIPerformanceHeader";

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

function renderHeader(key: RubroKey) {
  rubroKey = key;
  return render(
    <MantineProvider>
      <AIPerformanceHeader />
    </MantineProvider>,
  );
}

describe("AIPerformanceHeader (rubro-aware)", () => {
  it("siempre muestra el título fijo de la vista", () => {
    renderHeader("restaurante");
    expect(screen.getByRole("heading", { name: "Rendimiento IA" })).toBeInTheDocument();
  });

  it("enfoca el primaryKpi de gastronomía para restaurante (default)", () => {
    renderHeader("restaurante");
    expect(screen.getByText("Recurrencia de Compra")).toBeInTheDocument();
    expect(screen.getByText(/Restaurante/)).toBeInTheDocument();
  });

  it("enfoca el primaryKpi de salud/estética para peluquería, sin fugas de gastronomía", () => {
    renderHeader("peluqueria");
    expect(screen.getByText("Tasa No-Show")).toBeInTheDocument();
    expect(screen.queryByText("Recurrencia de Compra")).not.toBeInTheDocument();
  });
});
