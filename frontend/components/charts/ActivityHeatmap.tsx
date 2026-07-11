"use client";

import { APEXCHARTS_DEFAULTS, CHART_COLORS } from "@/lib/chart-config";
import { APPLE_BLUE } from "@/lib/theme-tokens";
import { Paper, Skeleton, Text } from "@mantine/core";
import type { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";

const ApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

const HOURS = ["00", "02", "04", "06", "08", "10", "12", "14", "16", "18", "20", "22"];
const DAYS = ["Dom", "Sáb", "Vie", "Jue", "Mié", "Mar", "Lun"];

export interface HeatmapDataPoint {
  dayIndex: number; // 0=Sun … 6=Sat
  hourIndex: number; // 0-11  (maps to HOURS)
  value: number;
}

interface ActivityHeatmapProps {
  data: HeatmapDataPoint[];
  isLoading?: boolean;
  title?: string;
}

function buildSeries(data: HeatmapDataPoint[]) {
  return DAYS.map((day, dayIdx) => ({
    name: day,
    data: HOURS.map((hour, hourIdx) => {
      const point = data.find((d) => d.dayIndex === 6 - dayIdx && d.hourIndex === hourIdx);
      return { x: `${hour}h`, y: point?.value ?? 0 };
    }),
  }));
}

export function ActivityHeatmap({
  data,
  isLoading,
  title = "Actividad por Hora",
}: ActivityHeatmapProps) {
  if (isLoading) return <Skeleton height={260} radius="md" />;

  const series = buildSeries(data);

  const options: ApexOptions = {
    ...APEXCHARTS_DEFAULTS,
    chart: { ...APEXCHARTS_DEFAULTS.chart, type: "heatmap" },
    dataLabels: { enabled: false },
    colors: [CHART_COLORS.primary],
    plotOptions: {
      heatmap: {
        shadeIntensity: 0.6,
        radius: 4,
        colorScale: {
          ranges: [
            { from: 0, to: 0, color: "var(--mantine-color-gray-2)", name: "Sin actividad" },
            { from: 1, to: 5, color: APPLE_BLUE[2], name: "Baja" },
            { from: 6, to: 15, color: APPLE_BLUE[4], name: "Media" },
            { from: 16, to: 999, color: CHART_COLORS.primary, name: "Alta" },
          ],
        },
      },
    },
    xaxis: {
      labels: { style: { fontFamily: "Inter, sans-serif", fontSize: "11px" } },
    },
    yaxis: {
      labels: { style: { fontFamily: "Inter, sans-serif", fontSize: "11px" } },
    },
    tooltip: {
      ...APEXCHARTS_DEFAULTS.tooltip,
      y: { formatter: (v: number) => `${v} eventos` },
    },
    legend: { show: false },
  };

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
        {title}
      </Text>
      <ApexChart type="heatmap" series={series} options={options} height={220} />
    </Paper>
  );
}
