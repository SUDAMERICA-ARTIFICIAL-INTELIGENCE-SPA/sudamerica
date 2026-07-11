"use client";

import { CHART_PALETTE, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import type { Lead } from "@/lib/types";
import { Paper, Skeleton, Text } from "@mantine/core";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface ChannelDistributionProps {
  leads: Lead[];
  isLoading?: boolean;
}

export function ChannelDistribution({ leads, isLoading }: ChannelDistributionProps) {
  if (isLoading) return <Skeleton height={220} radius="md" />;

  const counts: Record<string, number> = {};
  for (const lead of leads) {
    counts[lead.canal] = (counts[lead.canal] ?? 0) + 1;
  }

  const data = Object.entries(counts)
    .map(([canal, count]) => ({ name: canal, value: count }))
    .sort((a, b) => b.value - a.value);

  return (
    <Paper p="md" radius="md" shadow="sm">
      <Text
        fw={600}
        mb="sm"
        size="sm"
        c="dimmed"
        tt="uppercase"
        style={{ letterSpacing: "0.04em", fontSize: "11px" }}
      >
        Distribución por Canal
      </Text>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={75}
            dataKey="value"
            aria-label="Gráfico de distribución por canal"
          >
            {data.map((_, idx) => (
              <Cell key={idx} fill={CHART_PALETTE[idx % CHART_PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={RECHARTS_DEFAULTS.tooltipStyle}
            formatter={(value: number, name: string) => [`${value} leads`, name]}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
        </PieChart>
      </ResponsiveContainer>
    </Paper>
  );
}
