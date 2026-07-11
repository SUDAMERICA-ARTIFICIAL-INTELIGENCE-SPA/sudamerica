"use client";

import { useRubroLabels } from "@/hooks/useRubroLabels";
import { rubroSectorConfig } from "@/lib/rubros";
import { Group, Skeleton, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";

/**
 * Encabezado rubro-aware de la vista de Rendimiento IA (data-free).
 *
 * Muestra el título fijo + una línea de contexto que adapta el foco al sector del
 * tenant: el `primaryKpi` de SECTOR_CONFIG (Recurrencia de Compra para gastronomía,
 * Tasa No-Show para salud/estética, etc.). No inventa métricas — solo config. Mientras
 * carga el tenant muestra skeleton en vez de labels provisorios (patrón `SectorInsight`).
 */
export function AIPerformanceHeader() {
  const rubro = useRubroLabels();

  return (
    <Stack gap={4}>
      <Title order={2}>Rendimiento IA</Title>

      {rubro.isLoading ? (
        <Skeleton height={16} width={340} radius="sm" />
      ) : (
        <Group gap={8} align="center" wrap="nowrap">
          <ThemeIcon variant="light" color="amber" size="sm" radius="md" aria-hidden>
            <IconSparkles size={14} />
          </ThemeIcon>
          <Text size="sm" c="dimmed">
            Atención IA para tu {rubro.nombre} · foco del sector:{" "}
            <Text span fw={600} c="indigo">
              {rubroSectorConfig(rubro.key).primaryKpi}
            </Text>
          </Text>
        </Group>
      )}
    </Stack>
  );
}
