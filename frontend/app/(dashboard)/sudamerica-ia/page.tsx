"use client";

import { SudamericaChat } from "@/components/sudamerica/SudamericaChat";
import { PageHeader } from "@/components/ui/PageHeader";
import { Box, Group, Paper, Stack } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";

export default function SudamericaIaPage() {
  return (
    <Stack
      gap="md"
      style={{
        // Resta la altura del header sticky (--app-shell-header-height, ver
        // app/(dashboard)/layout.tsx) + el padding vertical del AppShell.Main (md, 32px)
        // + el padding vertical del contenedor centrado (CONTENT_PADDING_BLOCK×2, 48px).
        height: "calc(100dvh - var(--app-shell-header-height, 56px) - 80px)",
        minHeight: 0,
      }}
    >
      {/* Header */}
      <Group gap="sm" align="center" wrap="nowrap">
        <Box
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "var(--mantine-color-appleBlue-6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <IconSparkles size={20} color="white" />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <PageHeader title="Sudamérica AI" subtitle="Tu copiloto administrativo" />
        </Box>
      </Group>

      {/* Chat area */}
      <Paper
        radius="lg"
        withBorder
        style={{
          flex: 1,
          position: "relative",
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <SudamericaChat />
      </Paper>
    </Stack>
  );
}
