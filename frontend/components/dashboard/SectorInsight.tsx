"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { rubroSectorConfig } from "@/lib/rubros";
import { Badge, Group, Skeleton, Stack, Text } from "@mantine/core";

/**
 * Widget rubro-aware (data-free): muestra el KPI clave y los benchmarks LATAM del
 * sector del tenant, tomados de SECTOR_CONFIG. No inventa métricas — es contexto de
 * config que orienta al dueño sobre qué mirar en su rubro.
 */
export function SectorInsight() {
  const rubro = useRubroLabels();

  if (rubro.isLoading) {
    return (
      <SectionCard title="KPI clave de tu sector" fullHeight>
        <Stack gap="sm">
          <Skeleton height={26} width="70%" radius="sm" />
          <Skeleton height={12} width="90%" radius="sm" />
          <Skeleton height={12} width="80%" radius="sm" />
        </Stack>
      </SectionCard>
    );
  }

  const sector = rubroSectorConfig(rubro.key);
  const benchmarks = sector.benchmarks.slice(0, 3);

  return (
    <SectionCard title="KPI clave de tu sector" fullHeight>
      <Stack gap="sm">
        <Group gap={8} align="center" wrap="nowrap">
          <Text fw={700} style={{ fontSize: "22px", lineHeight: 1.15 }}>
            {sector.primaryKpi}
          </Text>
          <Badge variant="light" color="grape" radius="sm">
            {sector.label}
          </Badge>
        </Group>

        <Stack gap={6} mt={4}>
          {benchmarks.map((b) => (
            <Group key={b.metric} gap={8} align="baseline" wrap="nowrap">
              <Text size="sm" fw={600} c="indigo" style={{ whiteSpace: "nowrap" }}>
                {b.value}
              </Text>
              <Text size="sm">{b.metric}</Text>
              <Text size="xs" c="dimmed" style={{ flex: 1, minWidth: 0 }} truncate="end">
                {b.description}
              </Text>
            </Group>
          ))}
        </Stack>
      </Stack>
    </SectionCard>
  );
}
