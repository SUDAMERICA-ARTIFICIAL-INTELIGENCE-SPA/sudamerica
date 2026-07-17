"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { CHART_COLORS, CHART_PALETTE, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import { useSegmentacion } from "@/hooks/useLentes";
import { Badge, SimpleGrid, Skeleton, Stack, Table } from "@mantine/core";
import { IconUsers } from "@tabler/icons-react";
import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

const FALLBACK_COLOR = "gray";
const SEG_COLORS: Record<string, string> = {
  NUEVO: "blue",
  OCASIONAL: "cyan",
  FRECUENTE: "teal",
  VIP: "yellow",
  INACTIVO: "gray",
};

export default function Page() {
  const { data, isLoading } = useSegmentacion();
  const rows = data ?? [];

  const totalClientes = useMemo(() => rows.reduce((s, r) => s + Number(r.cantidad), 0), [rows]);
  const topGasto = useMemo(
    () => rows.reduce<(typeof rows)[number] | null>((best, r) => (best && Number(best.total_gastado) >= Number(r.total_gastado) ? best : r), null),
    [rows],
  );

  return (
    <Stack gap="lg">
      <PageHeader title="Segmentos" subtitle="Distribución de clientes por segmento de valor y comportamiento de gasto" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Total clientes" value={totalClientes} isLoading={isLoading} icon={<IconUsers size={18} />} />
        <KpiCard
          title="Segmento top (gasto)"
          value={topGasto ? Number(topGasto.total_gastado) : 0}
          prefix="$"
          isLoading={isLoading}
          color="teal"
          description={topGasto ? topGasto.segmento : ""}
        />
      </SimpleGrid>

      <SectionCard title="Clientes por segmento">
        {isLoading ? (
          <Skeleton height={280} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState icon={<IconUsers size={40} />} title="Sin segmentos" description="Aún no hay clientes segmentados." />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows} margin={RECHARTS_DEFAULTS.margin}>
              <CartesianGrid {...RECHARTS_DEFAULTS.gridStyle} />
              <XAxis dataKey="segmento" {...RECHARTS_DEFAULTS.axisStyle} />
              <YAxis {...RECHARTS_DEFAULTS.axisStyle} width={40} />
              <Tooltip contentStyle={RECHARTS_DEFAULTS.tooltipStyle} formatter={(v: number) => [`${Number(v)} clientes`, "Cantidad"]} />
              <Bar dataKey="cantidad" name="Clientes" radius={[4, 4, 0, 0]}>
                {rows.map((r, i) => (
                  <Cell key={r.segmento} fill={CHART_PALETTE[i % CHART_PALETTE.length] ?? CHART_COLORS.primary} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <SectionCard title="Detalle por segmento">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay segmentos para mostrar." />
        ) : (
          <Table.ScrollContainer minWidth={560}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Segmento</Table.Th>
                  <Table.Th ta="right">Clientes</Table.Th>
                  <Table.Th ta="right">Total gastado</Table.Th>
                  <Table.Th ta="right">Frecuencia prom.</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.segmento}>
                    <Table.Td>
                      <Badge variant="light" color={SEG_COLORS[r.segmento] ?? FALLBACK_COLOR} radius="sm">{r.segmento}</Badge>
                    </Table.Td>
                    <Table.Td ta="right">{Number(r.cantidad)}</Table.Td>
                    <Table.Td ta="right">{clp(Number(r.total_gastado))}</Table.Td>
                    <Table.Td ta="right">{`${Math.round(Number(r.avg_frecuencia_dias))} días`}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </SectionCard>
    </Stack>
  );
}
