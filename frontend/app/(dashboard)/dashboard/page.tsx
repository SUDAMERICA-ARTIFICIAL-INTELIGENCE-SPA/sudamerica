"use client";

import { RevenueChart } from "@/components/charts/RevenueChart";
import { NextBestActions } from "@/components/dashboard/NextBestActions";
import { SectorInsight } from "@/components/dashboard/SectorInsight";
import { SmartAlertsTable } from "@/components/dashboard/SmartAlertsTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { useDashboardKpis, useRevenueData } from "@/hooks/useMetricas";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useAuth } from "@/lib/auth";
import { RUBRO_DEFAULT } from "@/lib/rubros";
import { Grid, SimpleGrid, Stack } from "@mantine/core";
import {
  IconCash,
  IconPercentage,
  IconPigMoney,
  IconRobot,
  IconUserPlus,
} from "@tabler/icons-react";

function metaAttainmentLabel(ventas: number, meta: number): string {
  // El tipo declara `number`, pero la respuesta de la API no está validada con
  // Zod (es un cast): datos parciales llegan como undefined/NaN → guardar aquí.
  if (!Number.isFinite(meta) || meta <= 0) return "Sin meta definida";
  const pct = Number.isFinite(ventas) ? (ventas / meta) * 100 : 0;
  return `${pct.toFixed(0)}% de la meta ($${meta.toLocaleString("es-CL")})`;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const rubro = useRubroLabels();
  const { data: kpis, isLoading } = useDashboardKpis();
  const { data: revenue, isLoading: revenueLoading } = useRevenueData("month");

  // Rubro-aware: restaurante conserva "Leads"; el resto habla de "Clientes".
  const nuevosLabel = rubro.key === RUBRO_DEFAULT ? "Nuevos Leads" : "Nuevos Clientes";
  const firstName = user?.nombre?.split(" ")[0] ?? "";
  const revenueSparkline =
    revenue && revenue.length > 1 ? revenue.map((point) => point.revenue_real) : [];

  return (
    <Stack gap="lg">
      <PageHeader
        title={firstName ? `Hola, ${firstName}` : "Resumen Ejecutivo"}
        subtitle="Estado de tu negocio de un vistazo — ¿qué requiere tu atención hoy?"
      />

      {/* Row 1 — 5 KPIs (Z-pattern, regla de los 6 segundos) */}
      <SimpleGrid
        cols={{ base: 1, xs: 2, sm: 3, lg: 5 }}
        spacing="md"
        aria-label="Indicadores clave"
      >
        <StatCard
          label="Ventas del Mes"
          value={kpis?.ventas_mes ?? 0}
          prefix="$"
          loading={isLoading}
          description={kpis ? metaAttainmentLabel(kpis.ventas_mes, kpis.meta_mes) : ""}
          sparklineData={revenueSparkline}
          icon={<IconCash size={16} />}
        />
        <StatCard
          label={nuevosLabel}
          value={kpis?.nuevos_leads ?? 0}
          loading={isLoading}
          icon={<IconUserPlus size={16} />}
        />
        <StatCard
          label="Conversión"
          value={kpis?.tasa_conversion ?? 0}
          suffix="%"
          decimals={1}
          loading={isLoading}
          icon={<IconPercentage size={16} />}
        />
        <StatCard
          label="Atendidas por IA"
          value={kpis?.ia_atendidas ?? 0}
          loading={isLoading}
          description={
            kpis && Number.isFinite(kpis.ia_roi) ? `ROI IA ${kpis.ia_roi.toFixed(0)}%` : ""
          }
          icon={<IconRobot size={16} />}
        />
        <StatCard
          label="Ahorro con IA"
          value={kpis?.ahorro_ia_usd ?? 0}
          prefix="$"
          loading={isLoading}
          icon={<IconPigMoney size={16} />}
        />
      </SimpleGrid>

      {/* Row 2 — Revenue real vs forecast (2/3) + Smart Alerts (1/3) */}
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 8 }}>
          <SectionCard title="Ingresos reales" fullHeight>
            <RevenueChart data={revenue ?? []} isLoading={revenueLoading} bare />
          </SectionCard>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <SmartAlertsTable />
        </Grid.Col>
      </Grid>

      {/* Row 3 — Requiere tu atención (2/3) + KPI de sector rubro-aware (1/3) */}
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 8 }}>
          <SectionCard title="Requiere tu atención" fullHeight>
            <NextBestActions />
          </SectionCard>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <SectorInsight />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
