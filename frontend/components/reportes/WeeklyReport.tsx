"use client";

import { RevenueChart } from "@/components/charts/RevenueChart";
import { TopProductsList } from "@/components/reportes/TopProductsList";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { useOperationalSummary, useRevenueData, useTopProducts } from "@/hooks/useMetricas";
import { Grid, SimpleGrid } from "@mantine/core";
import { IconBox, IconCash, IconReceipt, IconShoppingBag } from "@tabler/icons-react";

export function WeeklyReport() {
  const { data: summary, isLoading } = useOperationalSummary("week");
  const { data: revenue, isLoading: revenueLoading } = useRevenueData("week");
  const { data: topProducts, isLoading: topProductsLoading } = useTopProducts("week", 5);

  return (
    <Grid gutter="md">
      <Grid.Col span={12}>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" aria-label="KPIs semanales">
          <StatCard
            label="Ingresos Semana"
            value={summary?.revenue_total ?? 0}
            prefix="$"
            loading={isLoading}
            icon={<IconCash size={16} />}
          />
          <StatCard
            label="Pedidos Entregados"
            value={summary?.pedidos_entregados ?? 0}
            loading={isLoading}
            icon={<IconShoppingBag size={16} />}
          />
          <StatCard
            label="Items Vendidos"
            value={summary?.items_vendidos ?? 0}
            loading={isLoading}
            icon={<IconBox size={16} />}
          />
          <StatCard
            label="Ticket Promedio"
            value={summary?.ticket_promedio ?? 0}
            prefix="$"
            loading={isLoading}
            icon={<IconReceipt size={16} />}
          />
        </SimpleGrid>
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 8 }}>
        <SectionCard title="Ingresos reales" fullHeight>
          <RevenueChart data={revenue ?? []} isLoading={revenueLoading} bare />
        </SectionCard>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 4 }}>
        <SectionCard title="Top Productos de la Semana" fullHeight>
          <TopProductsList
            title="Top Productos de la Semana"
            products={topProducts ?? []}
            isLoading={topProductsLoading}
            bare
          />
        </SectionCard>
      </Grid.Col>
    </Grid>
  );
}
