"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useTesoreria } from "@/hooks/useLentes";
import { CHART_COLORS, CHART_PALETTE, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import { SimpleGrid, Skeleton, Stack, Table } from "@mantine/core";
import { useMemo } from "react";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

export default function Page() {
  const { data, isLoading } = useTesoreria();
  const rows = useMemo(
    () => (data?.por_metodo ?? []).map((m) => ({ metodo: m.metodo, saldo: Number(m.saldo), movimientos: Number(m.movimientos) })),
    [data],
  );

  return (
    <Stack gap="lg">
      <PageHeader title="Tesorería" subtitle="Saldo disponible por medio de pago" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Saldo total" value={Number(data?.saldo_total ?? 0)} prefix="$" isLoading={isLoading} color="teal" />
        <KpiCard title="Medios de pago" value={rows.length} isLoading={isLoading} color="blue" />
      </SimpleGrid>

      <SectionCard title="Saldo por medio de pago">
        {isLoading ? (
          <Skeleton height={280} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay saldos de tesorería registrados." />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={rows} dataKey="saldo" nameKey="metodo" cx="50%" cy="50%" outerRadius={100} innerRadius={55} paddingAngle={2}>
                {rows.map((r, i) => (
                  <Cell key={r.metodo} fill={CHART_PALETTE[i % CHART_PALETTE.length] ?? CHART_COLORS.primary} />
                ))}
              </Pie>
              <Tooltip contentStyle={RECHARTS_DEFAULTS.tooltipStyle} formatter={(v: number) => clp(Number(v))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <SectionCard title="Detalle">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay saldos de tesorería registrados." />
        ) : (
          <Table.ScrollContainer minWidth={420}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Medio de pago</Table.Th>
                  <Table.Th ta="right">Saldo</Table.Th>
                  <Table.Th ta="right">Movimientos</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.metodo}>
                    <Table.Td>{r.metodo}</Table.Td>
                    <Table.Td ta="right">{clp(r.saldo)}</Table.Td>
                    <Table.Td ta="right">{r.movimientos}</Table.Td>
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
