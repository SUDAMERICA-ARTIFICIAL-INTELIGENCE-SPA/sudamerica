"use client";

import "@/app/globals.css";
import "@total-typescript/ts-reset";
import { APPLE_BLUE, DARK_NEUTRAL, RADIUS, SHADOWS_DARK, SHADOWS_LIGHT } from "@/lib/theme-tokens";
import { ColorSchemeScript, MantineProvider, createTheme, virtualColor } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Inter } from "next/font/google";
import { type ReactNode, useState } from "react";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
});

const theme = createTheme({
  // inter.style.fontFamily = nombre hasheado del Inter self-hosted (next/font);
  // sin él, máquinas sin Inter instalada caerían al sans-serif genérico.
  fontFamily: `${inter.style.fontFamily}, Inter, sans-serif`,
  // Índigo built-in de Mantine (#4C6EF5 en shade 6) — look pre-Apple del repo.
  primaryColor: "indigo",
  colors: {
    // Alias-compat: `appleBlue` sigue registrado pero con la tupla índigo
    // (ver lib/theme-tokens.ts) para no romper sus referencias existentes.
    appleBlue: APPLE_BLUE,
    // Paleta dark azul-pizarra original — subtle blue-slate tint
    dark: DARK_NEUTRAL,
    // Warm gastronomy accent
    amber: [
      "#FFF8E1",
      "#FFECB3",
      "#FFE082",
      "#FFD54F",
      "#FFCA28",
      "#FFC107",
      "#FFB300",
      "#FFA000",
      "#FF8F00",
      "#FF6F00",
    ],
    // Surface color that adapts to color scheme
    surface: virtualColor({
      name: "surface",
      dark: "dark",
      light: "gray",
    }),
  },
  radius: {
    default: `${RADIUS.md}px`,
    xs: "6px",
    sm: "8px",
    md: `${RADIUS.md}px`,
    lg: `${RADIUS.lg}px`,
    xl: `${RADIUS.xl}px`,
  },
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "16px",
    lg: "24px",
    xl: "32px",
  },
  // Sombras densas pre-Apple (see lib/theme-tokens.ts for the source values)
  shadows: SHADOWS_LIGHT,
  other: {
    cardShadow: SHADOWS_LIGHT.sm,
    cardShadowDark: SHADOWS_DARK.sm,
  },
  components: {
    Card: {
      defaultProps: {
        radius: "md",
        shadow: "sm",
      },
    },
    Paper: {
      defaultProps: {
        radius: "md",
      },
    },
    Button: {
      defaultProps: {
        radius: "sm",
      },
    },
    Modal: {
      defaultProps: {
        radius: "lg",
        shadow: "xl",
      },
    },
    Drawer: {
      defaultProps: {
        shadow: "xl",
      },
    },
    TextInput: {
      defaultProps: {
        radius: "md",
      },
    },
    PasswordInput: {
      defaultProps: {
        radius: "md",
      },
    },
    Select: {
      defaultProps: {
        radius: "md",
      },
    },
    NumberInput: {
      defaultProps: {
        radius: "md",
      },
    },
    Skeleton: {
      defaultProps: {
        radius: "md",
      },
    },
    Tooltip: {
      defaultProps: {
        radius: "sm",
      },
    },
  },
});

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <ColorSchemeScript defaultColorScheme="dark" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/logo.png" type="image/png" />
        <link rel="apple-touch-icon" href="/logo.png" />
        <title>Sudamérica AI</title>
      </head>
      <body className={inter.variable}>
        <MantineProvider theme={theme} defaultColorScheme="dark">
          <ModalsProvider>
            <Notifications position="top-right" zIndex={9999} />
            <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
          </ModalsProvider>
        </MantineProvider>
      </body>
    </html>
  );
}
