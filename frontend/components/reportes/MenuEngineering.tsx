"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useMenuEngineering } from "@/hooks/useMetricas";
import type { MenuEngineeringItem } from "@/lib/types";
import { Badge, Card, Group, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconDog, IconFlame, IconPuzzle, IconTractor } from "@tabler/icons-react";

const CLASSIFICATION_CONFIG: Record<
  string,
  { label: string; color: string; icon: React.ReactNode; description: string }
> = {
  STAR: {
    label: "Estrella",
    color: "green",
    icon: <IconFlame size={14} />,
    description: "Alta popularidad + Alto margen",
  },
  PUZZLE: {
    label: "Puzzle",
    color: "yellow",
    icon: <IconPuzzle size={14} />,
    description: "Baja popularidad + Alto margen",
  },
  PLOWHORSE: {
    label: "Caballo de tiro",
    color: "blue",
    icon: <IconTractor size={14} />,
    description: "Alta popularidad + Bajo margen",
  },
  DOG: {
    label: "Perro",
    color: "red",
    icon: <IconDog size={14} />,
    description: "Baja popularidad + Bajo margen",
  },
};

function ClassificationSummary({ items }: { items: MenuEngineeringItem[] }) {
  const counts = items.reduce(
    (acc, item) => {
      acc[item.clasificacion] = (acc[item.clasificacion] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
      {Object.entries(CLASSIFICATION_CONFIG).map(([key, config]) => (
        <Card key={key} padding="md" radius="md" withBorder>
          <Group gap="xs" mb={4}>
            {config.icon}
            <Text size="sm" fw={600}>
              {config.label}
            </Text>
          </Group>
          <Text size="xl" fw={700} c={config.color}>
            {counts[key] || 0}
          </Text>
          <Text size="xs" c="dimmed">
            {config.description}
          </Text>
        </Card>
      ))}
    </SimpleGrid>
  );
}

export function MenuEngineering() {
  const { data: items, isLoading } = useMenuEngineering("month");

  if (isLoading) {
    return (
      <Stack gap="md">
        <Skeleton height={80} />
        <Skeleton height={300} />
      </Stack>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card padding="xl" radius="md" withBorder>
        <EmptyState
          icon={<IconPuzzle size={40} color="var(--mantine-color-gray-5)" />}
          title="Sin datos de ventas"
          description="Registra ventas para ver el analisis de ingenieria de menu. Clasificaremos cada plato como Estrella, Puzzle, Caballo de tiro o Perro."
        />
      </Card>
    );
  }

  return (
    <Stack gap="md">
      <ClassificationSummary items={items} />

      <SectionCard title="Detalle por plato" noBodyPadding>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Plato</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Unidades</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Revenue</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>% del total</Table.Th>
              <Table.Th>Clasificacion</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => {
              const config = CLASSIFICATION_CONFIG[item.clasificacion];
              return (
                <Table.Tr key={item.producto_id}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {item.nombre}
                    </Text>
                  </Table.Td>
                  <Table.Td className="num-tabular">{item.unidades_vendidas}</Table.Td>
                  <Table.Td className="num-tabular">
                    ${item.revenue.toLocaleString("es-CL")}
                  </Table.Td>
                  <Table.Td className="num-tabular">{item.margen_pct.toFixed(1)}%</Table.Td>
                  <Table.Td>
                    <Badge
                      color={config?.color ?? "gray"}
                      variant="light"
                      leftSection={config?.icon}
                      aria-label={`Clasificacion: ${config?.label}`}
                    >
                      {config?.label ?? item.clasificacion}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </SectionCard>
    </Stack>
  );
}
