import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { Proximamente } from "./Proximamente";

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

describe("<Proximamente> — placeholder único para subs sin ruta", () => {
  it("monta con label + badge Próximamente y no queda vacío", () => {
    render(
      <MantineProvider>
        <Proximamente label="Notificaciones" categoria="Inicio" vistas={["No leídas"]} />
      </MantineProvider>,
    );
    expect(screen.getByText("Notificaciones")).toBeDefined();
    expect(screen.getByText("Próximamente")).toBeDefined();
    expect(screen.getByText("Inicio")).toBeDefined();
    expect(screen.getByText("No leídas")).toBeDefined();
  });

  it("monta graceful sin categoría ni vistas (sub desconocida)", () => {
    const { container } = render(
      <MantineProvider>
        <Proximamente label="Esta sección" />
      </MantineProvider>,
    );
    expect(screen.getByText("Esta sección")).toBeDefined();
    expect(container.textContent).not.toBe("");
  });
});
