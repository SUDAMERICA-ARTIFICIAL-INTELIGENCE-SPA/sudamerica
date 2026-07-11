"use client";

import { useUiStore } from "@/stores/ui-store";
import { AppShell, Burger } from "@mantine/core";

/**
 * Header mínimo — SOLO móvil (`hiddenFrom="sm"`, y el shell le da altura 0 en `sm+`).
 * En escritorio no existe: la marca, la navegación y las acciones globales
 * (buscar / tema / notificaciones / Copiloto) viven todas en el `Sidebar`,
 * como en el front de prod (standalone @4c77479). Su única razón de ser es el
 * Burger: sin él, en móvil el sidebar queda colapsado y no hay forma de abrirlo.
 */
export function TopBar() {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <AppShell.Header
      hiddenFrom="sm"
      style={{
        backgroundColor: "var(--mantine-color-body)",
        borderBottom: "1px solid var(--mantine-color-default-border)",
        display: "flex",
        alignItems: "center",
        paddingLeft: 16,
        paddingRight: 16,
      }}
    >
      <Burger
        opened={sidebarOpen}
        onClick={toggleSidebar}
        size="sm"
        aria-label={sidebarOpen ? "Cerrar menu lateral" : "Abrir menu lateral"}
      />
    </AppShell.Header>
  );
}
