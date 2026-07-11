"use client";

import { StatCard } from "@/components/ui/StatCard";
import { useDashboardKpis } from "@/hooks/useMetricas";
import { SimpleGrid } from "@mantine/core";
import { IconBrain, IconClock, IconCurrencyDollar, IconRobot } from "@tabler/icons-react";

export function AIMetrics() {
  const { data: kpis, isLoading } = useDashboardKpis();

  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md" aria-label="Métricas de IA">
      <StatCard
        label="Auto-Resolución"
        value={kpis?.ia_tasa_auto_resolucion ?? 0}
        suffix="%"
        decimals={1}
        description={`${kpis?.ia_auto_resueltas ?? 0} de ${kpis?.ia_atendidas ?? 0} conv. sin humano`}
        icon={<IconRobot size={16} />}
        loading={isLoading}
      />
      <StatCard
        label="Costo / Conversación"
        value={kpis?.ia_costo_por_conversacion ?? 0}
        prefix="$"
        decimals={4}
        description={`$${(kpis?.ia_costo_tokens_usd ?? 0).toFixed(2)} total en ${kpis?.ia_total_tokens ?? 0} tokens`}
        icon={<IconCurrencyDollar size={16} />}
        loading={isLoading}
      />
      <StatCard
        label="Horas Ahorradas"
        value={kpis?.ia_horas_ahorradas ?? 0}
        suffix="h"
        decimals={1}
        description="5min × conv. auto-resuelta"
        icon={<IconClock size={16} />}
        loading={isLoading}
      />
      <StatCard
        label="ROI IA"
        value={kpis?.ia_roi ?? 0}
        suffix="%"
        decimals={0}
        description={`ahorro $${(kpis?.ahorro_ia_usd ?? 0).toFixed(2)} vs costo $${(kpis?.ia_costo_tokens_usd ?? 0).toFixed(2)}`}
        icon={<IconBrain size={16} />}
        loading={isLoading}
      />
    </SimpleGrid>
  );
}
