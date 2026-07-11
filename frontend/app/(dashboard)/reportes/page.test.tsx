import { type RubroKey, getRubroDef } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import ReportesPage from "./page";

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
// Los paneles fetchean sus propios hooks: se stubean a null para aislar el gating de tabs.
vi.mock("@/components/reportes/DailyReport", () => ({ DailyReport: () => null }));
vi.mock("@/components/reportes/FinancialDashboard", () => ({ FinancialDashboard: () => null }));
vi.mock("@/components/reportes/MenuEngineering", () => ({ MenuEngineering: () => null }));
vi.mock("@/components/reportes/MonthlyReport", () => ({ MonthlyReport: () => null }));
vi.mock("@/components/reportes/WeeklyReport", () => ({ WeeklyReport: () => null }));

function renderPage(key: RubroKey) {
  rubroKey = key;
  return render(
    <MantineProvider>
      <ReportesPage />
    </MantineProvider>,
  );
}

describe("ReportesPage — tab Menu Engineering rubro-aware", () => {
  it("muestra el tab Menu Engineering para restaurante (gastronomía)", () => {
    renderPage("restaurante");
    expect(screen.getByText("Menu Engineering")).toBeInTheDocument();
    // Tabs genéricos siempre presentes.
    expect(screen.getByText("Financiero")).toBeInTheDocument();
    expect(screen.getByText("Diario")).toBeInTheDocument();
  });

  it("oculta Menu Engineering para peluquería (salud/estética)", () => {
    renderPage("peluqueria");
    expect(screen.queryByText("Menu Engineering")).not.toBeInTheDocument();
    // Los reportes genéricos siguen visibles.
    expect(screen.getByText("Diario")).toBeInTheDocument();
    expect(screen.getByText("Mensual")).toBeInTheDocument();
  });

  it("oculta Menu Engineering para ferretería (retail)", () => {
    renderPage("ferreteria");
    expect(screen.queryByText("Menu Engineering")).not.toBeInTheDocument();
  });
});
