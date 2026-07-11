import "@mantine/core/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";
import "./globals.css";

import { ColorSchemeScript, MantineProvider, createTheme } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Sudamerica Admin — Sudamérica AI",
  description: "Panel de administración interno",
};

const theme = createTheme({
  fontFamily: "Inter, sans-serif",
  primaryColor: "indigo",
  components: {
    Card: { defaultProps: { radius: "md", shadow: "sm" } },
    Button: { defaultProps: { radius: "sm" } },
  },
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <ColorSchemeScript />
      </head>
      <body>
        <MantineProvider theme={theme}>
          <ModalsProvider>
            <Notifications position="top-right" />
            <Providers>{children}</Providers>
          </ModalsProvider>
        </MantineProvider>
      </body>
    </html>
  );
}
