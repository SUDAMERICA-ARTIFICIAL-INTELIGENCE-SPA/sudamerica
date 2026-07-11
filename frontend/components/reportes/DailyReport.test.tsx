import { type RubroKey, getRubroDef } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { DailyReport } from "./DailyReport";

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
vi.mock("@/hooks/useMetricas", () => ({
  useOperationalSummary: () => ({ data: undefined, isLoading: false }),
  useRevenueData: () => ({ data: [], isLoading: false }),
  useTopProducts: () => ({ data: [], isLoading: false }),
}));
vi.mock("@/components/charts/RevenueChart", () => ({ RevenueChart: () => null }));
vi.mock("@/components/reportes/TopProductsList", () => ({ TopProductsList: () => null }));

function renderReport(key: RubroKey) {
  rubroKey = key;
  return render(
    <MantineProvider>
      <DailyReport />
    </MantineProvider>,
  );
}

describe("DailyReport — byte-identidad restaurante (F7 M9)", () => {
  it("restaurante conserva exactamente los títulos actuales", () => {
    renderReport("restaurante");
    for (const title of [
      "Ingresos Hoy",
      "Pedidos Entregados",
      "Items Vendidos",
      "Ticket Promedio",
      "Comandas Abiertas",
      "Canceladas",
    ]) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
  });

  it("rubro genérico usa título neutro en género (sin 'Abiertas')", () => {
    renderReport("ferreteria");
    expect(screen.getByText("Pedidos en Curso")).toBeInTheDocument();
    expect(screen.queryByText(/Abiertas/)).not.toBeInTheDocument();
  });
});
