"use client";

import { APEXCHARTS_DEFAULTS, CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import type { RevenueDataPoint } from "@/lib/types";
import { Paper, Skeleton, Text } from "@mantine/core";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface RevenueChartProps {
  data: RevenueDataPoint[];
  isLoading?: boolean;
  /** Omite el Paper + título propios — para cuando ya viene envuelto en SectionCard. */
  bare?: boolean;
}

function formatCurrency(value: number) {
  return `$${Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(value)}`;
}

function formatDate(fecha: string) {
  const date = new Date(fecha);
  return date.toLocaleDateString("es-CL", { day: "2-digit", month: "short" });
}

export function RevenueChart({ data, isLoading, bare = false }: RevenueChartProps) {
  if (isLoading) {
    return <Skeleton height={280} radius="md" />;
  }

  const chart = (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={RECHARTS_DEFAULTS.margin}>
        <CartesianGrid
          stroke={APEXCHARTS_DEFAULTS.grid.borderColor}
          strokeDasharray={String(APEXCHARTS_DEFAULTS.grid.strokeDashArray)}
          vertical={false}
        />
        <XAxis
          dataKey="fecha"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(value: number) => `$${(value / 1000).toFixed(0)}k`}
          tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={RECHARTS_DEFAULTS.tooltipStyle}
          formatter={(value: number) => [formatCurrency(value), "Ingresos"]}
          labelFormatter={formatDate}
        />
        <Area
          type="monotone"
          dataKey="revenue_real"
          fill={CHART_COLORS.primary}
          stroke={CHART_COLORS.primary}
          fillOpacity={0.12}
          strokeWidth={2}
          activeDot={{ r: 5, fill: CHART_COLORS.primary }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );

  if (bare) {
    return chart;
  }

  return (
    <Paper p="md" radius="md" shadow="sm">
      <Text
        fw={600}
        mb="md"
        size="sm"
        c="dimmed"
        tt="uppercase"
        style={{ letterSpacing: "0.04em", fontSize: "11px" }}
      >
        Ingresos reales
      </Text>
      {chart}
    </Paper>
  );
}
