"use client";

import { RevenueChart } from "@/components/charts/RevenueChart";
import { TopProductsList } from "@/components/reportes/TopProductsList";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { useOperationalSummary, useRevenueData, useTopProducts } from "@/hooks/useMetricas";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import { Grid, SimpleGrid } from "@mantine/core";
import {
  IconBox,
  IconCash,
  IconChecklist,
  IconReceipt,
  IconShoppingBag,
  IconX,
} from "@tabler/icons-react";

export function DailyReport() {
  const rubro = useRubroLabels();
  const { data: summary, isLoading } = useOperationalSummary("day");
  const { data: revenue, isLoading: revenueLoading } = useRevenueData("month");
  const { data: topProducts, isLoading: topProductsLoading } = useTopProducts("day", 5);

  // "en Curso" es neutro en género ("Pedidos Abiertas" ✗); restaurante byte-idéntico.
  const comandasAbiertasTitle =
    rubro.key === RUBRO_DEFAULT ? "Comandas Abiertas" : `${plural(rubro.labels.orden)} en Curso`;

  return (
    <Grid gutter="md">
      <Grid.Col span={12}>
        <SimpleGrid
          cols={{ base: 1, xs: 2, sm: 3, lg: 6 }}
          spacing="md"
          aria-label="Reporte diario"
        >
          <StatCard
            label="Ingresos Hoy"
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
          <StatCard
            label={comandasAbiertasTitle}
            value={summary?.comandas_abiertas ?? 0}
            loading={isLoading}
            description="Pendiente, en cocina o listas"
            icon={<IconChecklist size={16} />}
          />
          <StatCard
            label="Canceladas"
            value={summary?.comandas_canceladas ?? 0}
            loading={isLoading}
            icon={<IconX size={16} />}
          />
        </SimpleGrid>
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 8 }}>
        <SectionCard title="Ingresos reales" fullHeight>
          <RevenueChart data={revenue ?? []} isLoading={revenueLoading} bare />
        </SectionCard>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 4 }}>
        <SectionCard title="Top Productos de Hoy" fullHeight>
          <TopProductsList
            title="Top Productos de Hoy"
            products={topProducts ?? []}
            isLoading={topProductsLoading}
            bare
          />
        </SectionCard>
      </Grid.Col>
    </Grid>
  );
}
