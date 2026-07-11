"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface ROIBreakdownProps {
  timeSavedUsd: number;
  incrementalRevenue: number;
  saasPrice: number;
}

function formatUsd(v: number) {
  return `$${Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(v)}`;
}

export function ROIBreakdown({ timeSavedUsd, incrementalRevenue, saasPrice }: ROIBreakdownProps) {
  const data = [
    { name: "Tiempo\nahorrado", value: timeSavedUsd, color: CHART_COLORS.primary },
    { name: "Ventas\nincrementales", value: incrementalRevenue, color: CHART_COLORS.success },
    { name: "Costo\nSudamérica AI", value: -saasPrice, color: CHART_COLORS.danger },
  ];

  return (
    <SectionCard title="Desglose de beneficios vs costo">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={RECHARTS_DEFAULTS.margin}>
          <CartesianGrid
            stroke="var(--mantine-color-default-border)"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `$${Math.abs(v / 1000).toFixed(0)}k`}
            tick={{ fontSize: 11, fill: CHART_COLORS.neutral }}
            axisLine={false}
            tickLine={false}
            width={42}
          />
          <Tooltip
            contentStyle={RECHARTS_DEFAULTS.tooltipStyle}
            formatter={(value: number) => [formatUsd(Math.abs(value)), "Monto"]}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={entry.color} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              formatter={(v: number) => formatUsd(Math.abs(v))}
              style={{ fontSize: "11px", fill: CHART_COLORS.neutral, fontWeight: 600 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </SectionCard>
  );
}
