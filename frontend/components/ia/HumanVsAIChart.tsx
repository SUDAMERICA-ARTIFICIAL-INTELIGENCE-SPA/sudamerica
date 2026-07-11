"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useDashboardKpis, useWeeklyActivity } from "@/hooks/useMetricas";
import { CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import type { WeeklyActivityPoint } from "@/lib/types";
import { SimpleGrid, Skeleton } from "@mantine/core";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function HumanVsAIDonut({
  iaAtendidas,
  total,
  isLoading,
}: {
  iaAtendidas: number;
  total: number;
  isLoading: boolean;
}) {
  if (isLoading) return <Skeleton height={200} radius="md" />;

  const human = Math.max(total - iaAtendidas, 0);
  const data = [
    { name: "IA", value: iaAtendidas },
    { name: "Humano", value: human },
  ];

  return (
    <SectionCard title="Distribución IA vs Humano" fullHeight>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            aria-label="Gráfico de distribución IA vs Humano"
          >
            <Cell fill={CHART_COLORS.primary} />
            <Cell fill={CHART_COLORS.neutral} />
          </Pie>
          <Tooltip
            contentStyle={RECHARTS_DEFAULTS.tooltipStyle}
            formatter={(value: number, name: string) => [`${value} conversaciones`, name]}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
        </PieChart>
      </ResponsiveContainer>
    </SectionCard>
  );
}

function WeeklyHoursChart({
  weeklyData,
  isLoading,
}: {
  weeklyData: WeeklyActivityPoint[] | undefined;
  isLoading: boolean;
}) {
  if (isLoading) return <Skeleton height={200} radius="md" />;

  const data = weeklyData ?? [];

  return (
    <SectionCard title="Horas Atendidas / Semana" fullHeight>
      {data.length === 0 ? (
        <EmptyState
          icon="📊"
          title="Sin actividad semanal aún"
          description="Cuando haya conversaciones registradas, verás el reparto IA vs Humano por día."
        />
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={RECHARTS_DEFAULTS.margin}>
            <CartesianGrid
              stroke="var(--mantine-color-default-border)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={RECHARTS_DEFAULTS.tooltipStyle}
              formatter={(value: number, name: string) => [
                `${value}h`,
                name === "ia" ? "IA" : "Humano",
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
              formatter={(v) => (v === "ia" ? "IA" : "Humano")}
            />
            <Bar dataKey="ia" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
            <Bar dataKey="humano" fill={CHART_COLORS.neutral} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </SectionCard>
  );
}

export function HumanVsAIChart() {
  const { data: kpis, isLoading: isLoadingKpis } = useDashboardKpis();
  const { data: weeklyData, isLoading: isLoadingWeekly } = useWeeklyActivity();
  const iaAutoResueltas = kpis?.ia_auto_resueltas ?? 0;
  const totalConversaciones = kpis?.ia_atendidas ?? 0;
  const isLoading = isLoadingKpis || isLoadingWeekly;

  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
      <HumanVsAIDonut
        iaAtendidas={iaAutoResueltas}
        total={totalConversaciones}
        isLoading={isLoading}
      />
      <WeeklyHoursChart weeklyData={weeklyData} isLoading={isLoading} />
    </SimpleGrid>
  );
}
