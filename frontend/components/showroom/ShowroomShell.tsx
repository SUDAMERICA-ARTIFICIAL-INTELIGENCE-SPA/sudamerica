"use client";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { CONTENT_MAX_WIDTH, SIDEBAR_WIDTH } from "@/lib/theme-tokens";
import { useUiStore } from "@/stores/ui-store";
import { AppShell, Box } from "@mantine/core";
import type { ReactNode } from "react";

// Padding vertical del contenedor centrado — igual que (dashboard)/layout.
const CONTENT_PADDING_BLOCK = 24;

/**
 * Shell del showroom: mismo AppShell + Sidebar/TopBar/CommandPalette REALES del
 * dashboard, pero SIN `RequireAuth` ni el gate de onboarding/useTenant (la vitrina
 * no tiene backend). Los links del Sidebar apuntan dentro de `/showroom/<rubro>/…`
 * gracias al `ShowroomNavProvider` que envuelve este árbol.
 */
export function ShowroomShell({ children }: { children: ReactNode }) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);

  return (
    <AppShell
      layout="alt"
      navbar={{
        width: SIDEBAR_WIDTH,
        breakpoint: "sm",
        collapsed: { mobile: !sidebarOpen, desktop: false },
      }}
      header={{ height: { base: 44, sm: 0 } }}
      padding="md"
    >
      <TopBar />
      <Sidebar />
      <CommandPalette />
      <AppShell.Main>
        <Box
          style={{
            maxWidth: CONTENT_MAX_WIDTH,
            marginInline: "auto",
            paddingInline: "clamp(24px, 4vw, 32px)",
            paddingBlock: CONTENT_PADDING_BLOCK,
          }}
        >
          <ErrorBoundary>{children}</ErrorBoundary>
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
