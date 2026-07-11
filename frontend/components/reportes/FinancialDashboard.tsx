"use client";

import { StatCard } from "@/components/ui/StatCard";
import { useFinancialSummary } from "@/hooks/useMetricas";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import {
  Alert,
  Card,
  Group,
  Progress,
  SegmentedControl,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconCash,
  IconMoneybag,
  IconReceipt,
  IconShoppingBag,
  IconTrendingUp,
} from "@tabler/icons-react";
import { useState } from "react";

function formatCLP(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n))}`;
}

export function FinancialDashboard() {
  const [period, setPeriod] = useState<"day" | "week" | "month">("month");
  const { data, isLoading } = useFinancialSummary(period);
  const rubro = useRubroLabels();

  if (isLoading) {
    return (
      <Stack gap="md">
        <Skeleton height={40} />
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} height={100} />
          ))}
        </SimpleGrid>
      </Stack>
    );
  }

  const d = data ?? {
    total_ventas: 0,
    revenue: 0,
    cogs: 0,
    margen_bruto: 0,
    food_cost_pct: 0,
    margen_pct: 0,
    ticket_promedio: 0,
    items_vendidos: 0,
    productos_sin_costo: 0,
    period: "month",
  };

  const periodLabel = period === "day" ? "Hoy" : period === "week" ? "Esta semana" : "Este mes";

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>Resumen Financiero — {periodLabel}</Title>
        <SegmentedControl
          value={period}
          onChange={(v) => setPeriod(v as "day" | "week" | "month")}
          data={[
            { label: "Dia", value: "day" },
            { label: "Semana", value: "week" },
            { label: "Mes", value: "month" },
          ]}
          size="xs"
        />
      </Group>

      {d.productos_sin_costo > 0 && (
        <Alert
          icon={<IconAlertTriangle size={16} />}
          color="yellow"
          variant="light"
          title="Costos incompletos"
        >
          {d.productos_sin_costo} productos no tienen costo asignado. Ve a {rubro.labels.catalogo}{" "}
          &gt; editar producto para agregar el costo y obtener margenes reales.
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        <StatCard
          label="Total Ventas"
          value={d.total_ventas}
          loading={isLoading}
          icon={<IconShoppingBag size={16} />}
        />
        <StatCard
          label="Ingresos"
          value={d.revenue}
          prefix="$"
          loading={isLoading}
          icon={<IconCash size={16} />}
        />
        <StatCard
          label="Costo (COGS)"
          value={d.cogs}
          prefix="$"
          loading={isLoading}
          icon={<IconMoneybag size={16} />}
        />
        <StatCard
          label="Margen Bruto"
          value={d.margen_bruto}
          prefix="$"
          loading={isLoading}
          icon={<IconTrendingUp size={16} />}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        <StatCard
          label="Ticket Promedio"
          value={d.ticket_promedio}
          prefix="$"
          loading={isLoading}
          icon={<IconReceipt size={16} />}
        />
        <StatCard
          label="Items Vendidos"
          value={d.items_vendidos}
          loading={isLoading}
          icon={<IconShoppingBag size={16} />}
        />

        <Card padding="md" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
            Food Cost %
          </Text>
          <Text
            size="xl"
            fw={700}
            c={d.food_cost_pct > 35 ? "red" : d.food_cost_pct > 28 ? "yellow" : "green"}
          >
            {d.food_cost_pct.toFixed(1)}%
          </Text>
          <Progress
            value={Math.min(d.food_cost_pct, 100)}
            color={d.food_cost_pct > 35 ? "red" : d.food_cost_pct > 28 ? "yellow" : "green"}
            size="sm"
            mt={8}
            aria-label="Food cost percentage"
          />
          <Text size="xs" c="dimmed" mt={4}>
            Objetivo: 25-35%
          </Text>
        </Card>

        <Card padding="md" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
            Margen %
          </Text>
          <Text
            size="xl"
            fw={700}
            c={d.margen_pct >= 65 ? "green" : d.margen_pct >= 55 ? "yellow" : "red"}
          >
            {d.margen_pct.toFixed(1)}%
          </Text>
          <Progress
            value={Math.min(d.margen_pct, 100)}
            color={d.margen_pct >= 65 ? "green" : d.margen_pct >= 55 ? "yellow" : "red"}
            size="sm"
            mt={8}
            aria-label="Margin percentage"
          />
          <Text size="xs" c="dimmed" mt={4}>
            Objetivo: &gt;65%
          </Text>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
