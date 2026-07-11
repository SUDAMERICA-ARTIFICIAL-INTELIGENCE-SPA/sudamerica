import { AuthProvider } from "@/lib/auth";
import { activateDemo } from "@/lib/demo/state";
import { RUBRO_OPTIONS } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import ShowroomRubroPage from "./[rubro]/page";
import ShowroomPanel from "./page";

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

// next/link → <a> plano; next/navigation → stubs (params fijan restaurante).
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ rubro: "restaurante" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/showroom/restaurante",
}));

function withMantine(ui: ReactNode) {
  return <MantineProvider>{ui}</MantineProvider>;
}

describe("Showroom panel", () => {
  it("lista una cuenta/rubro por cada rubro del SSOT", () => {
    render(withMantine(<ShowroomPanel />));
    const links = screen.getAllByRole("link");
    // Auto-escala con el SSOT (RUBRO_OPTIONS deriva de RUBROS) → no se rehornea por rubro nuevo.
    expect(links).toHaveLength(RUBRO_OPTIONS.length);
  });
});

describe("Showroom dashboard demo (rubro-aware)", () => {
  it("renderiza el dashboard reutilizado sin error", async () => {
    activateDemo();
    // El guard de isDemoActive exige estar bajo /showroom.
    window.history.pushState({}, "", "/showroom/restaurante");
    render(
      withMantine(
        <AuthProvider>
          <ShowroomRubroPage />
        </AuthProvider>,
      ),
    );
    // Título estático del dashboard reutilizado → confirma que montó sin throw.
    expect(await screen.findByText("Requiere tu atención")).toBeInTheDocument();
    // Encabezado rubro-aware del showroom.
    expect(await screen.findByText("Restaurante")).toBeInTheDocument();
  });
});
