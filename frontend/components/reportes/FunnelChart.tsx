"use client";

import { APEXCHARTS_DEFAULTS, CHART_PALETTE } from "@/lib/chart-config";
import { LeadEstado } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import { Paper, Skeleton, Text } from "@mantine/core";
import type { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";

const ApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

const ESTADO_ORDER: LeadEstado[] = [
  LeadEstado.NUEVO,
  LeadEstado.CONTACTADO,
  LeadEstado.EN_PROCESO,
  LeadEstado.CONVERTIDO,
];

const ESTADO_LABELS: Record<LeadEstado, string> = {
  NUEVO: "Nuevo",
  CONTACTADO: "Contactado",
  EN_PROCESO: "En Proceso",
  CONVERTIDO: "Convertido",
  DESCARTADO: "Descartado",
};

interface FunnelChartProps {
  leads: Lead[];
  isLoading?: boolean;
}

export function FunnelChart({ leads, isLoading }: FunnelChartProps) {
  if (isLoading) return <Skeleton height={260} radius="md" />;

  const counts = ESTADO_ORDER.map((estado) => ({
    x: ESTADO_LABELS[estado],
    y: leads.filter((l) => l.estado === estado).length,
  }));

  const options: ApexOptions = {
    ...APEXCHARTS_DEFAULTS,
    chart: { ...APEXCHARTS_DEFAULTS.chart, type: "bar" },
    plotOptions: {
      bar: {
        horizontal: true,
        distributed: true,
        borderRadius: 6,
        dataLabels: { position: "center" },
      },
    },
    colors: CHART_PALETTE.slice(0, 4) as string[],
    dataLabels: {
      enabled: true,
      style: { fontSize: "12px", fontFamily: "Inter, sans-serif" },
    },
    xaxis: {
      categories: counts.map((c) => c.x),
      labels: { style: { fontFamily: "Inter, sans-serif", fontSize: "12px" } },
    },
    yaxis: {
      labels: { style: { fontFamily: "Inter, sans-serif", fontSize: "12px" } },
    },
    legend: { show: false },
    tooltip: {
      ...APEXCHARTS_DEFAULTS.tooltip,
      y: { formatter: (v: number) => `${v} prospectos` },
    },
  };

  const series = [{ name: "Prospectos", data: counts }];

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
        Embudo de Conversión
      </Text>
      <ApexChart type="bar" series={series} options={options} height={220} />
    </Paper>
  );
}
