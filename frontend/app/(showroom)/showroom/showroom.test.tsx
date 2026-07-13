import { AuthProvider } from "@/lib/auth";
import { activateDemo } from "@/lib/demo/state";
import { RUBRO_OPTIONS } from "@/lib/rubros";
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import ShowroomCatchAll from "./[rubro]/[[...ruta]]/page";
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
  useSearchParams: () => new URLSearchParams(),
}));
// next/image → <img> plano (evita el runtime de next/image en jsdom).
vi.mock("next/image", () => ({
  default: ({ src, alt, ...rest }: { src: string; alt: string }) => (
    // biome-ignore lint/a11y/useAltText: alt se pasa por props
    <img src={typeof src === "string" ? src : ""} alt={alt} {...rest} />
  ),
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

describe("Showroom navegable (shell real + base-path)", () => {
  it("monta el shell y el dashboard sin error, con hrefs bajo /showroom/<rubro>", async () => {
    activateDemo();
    // El guard de isDemoActive exige estar bajo /showroom.
    window.history.pushState({}, "", "/showroom/restaurante");
    render(
      withMantine(
        <AuthProvider>
          <ShowroomCatchAll />
        </AuthProvider>,
      ),
    );
    // Título estático del dashboard reutilizado → confirma que el shell + la
    // página (cargada por el registro de rutas) montaron sin throw.
    expect(await screen.findByText("Requiere tu atención")).toBeInTheDocument();
    // Core de Fase 2: los links del Sidebar navegan DENTRO del showroom.
    const links = screen.getAllByRole("link");
    const showroomLinks = links.filter((a) =>
      a.getAttribute("href")?.startsWith("/showroom/restaurante/"),
    );
    expect(showroomLinks.length).toBeGreaterThan(0);
  });
});
