"use client";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useTenant } from "@/hooks/useTenant";
import { AuthProvider, RequireAuth } from "@/lib/auth";
import { needsTenantOnboarding } from "@/lib/onboarding";
import { CONTENT_MAX_WIDTH, SIDEBAR_WIDTH } from "@/lib/theme-tokens";
import { useUiStore } from "@/stores/ui-store";
import { AppShell, Box, Center, Loader } from "@mantine/core";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

// Padding vertical del contenedor centrado — grid de 8px. `sudamerica-ia/page.tsx` resta
// este mismo valor × 2 (además del padding "md" del AppShell) al calcular su altura de viewport.
const CONTENT_PADDING_BLOCK = 24;

function DashboardShell({ children }: { children: ReactNode }) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const router = useRouter();
  const pathname = usePathname();
  const { data: tenant, isLoading } = useTenant();
  const onboardingRequired = needsTenantOnboarding(tenant);

  useEffect(() => {
    if (!isLoading && onboardingRequired && pathname !== "/onboarding") {
      router.replace("/onboarding");
    }
  }, [isLoading, onboardingRequired, pathname, router]);

  if (isLoading || onboardingRequired) {
    return (
      <Center mih="100vh">
        <Loader color="indigo" />
      </Center>
    );
  }

  return (
    <AppShell
      layout="alt"
      navbar={{
        width: SIDEBAR_WIDTH,
        breakpoint: "sm",
        collapsed: { mobile: !sidebarOpen, desktop: false },
      }}
      // Header solo en móvil (44px); en `sm+` mide 0 y el shell queda sin barra
      // superior — la marca y las acciones globales viven en el Sidebar.
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

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <RequireAuth>
        <DashboardShell>{children}</DashboardShell>
      </RequireAuth>
    </AuthProvider>
  );
}
