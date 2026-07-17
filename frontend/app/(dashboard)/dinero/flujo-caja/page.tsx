"use client";

import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import { useFlujoCaja } from "@/hooks/useLentes";
import { Group, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { useMemo } from "react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function mesLabel(periodo: string) {
  const [y, m] = periodo.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("es-CL", { month: "short" });
}

export default function Page() {
  const { data, isLoading } = useFlujoCaja(12);
  const rows = useMemo(() => (data ?? []).map((p) => ({ ...p, mes: mesLabel(p.periodo) })), [data]);
  const totals = useMemo(() => {
    const ingresos = rows.reduce((s, r) => s + Number(r.ingresos), 0);
    const egresos = rows.reduce((s, r) => s + Number(r.egresos), 0);
    return { ingresos, egresos, neto: ingresos - egresos };
  }, [rows]);

  return (
    <Stack gap="lg">
      <PageHeader title="Flujo de caja" subtitle="Ingresos (ventas) vs egresos (compras a proveedores), últimos 12 meses" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Ingresos (12m)" value={totals.ingresos} prefix="$" isLoading={isLoading} color="teal" />
        <KpiCard title="Egresos (12m)" value={totals.egresos} prefix="$" isLoading={isLoading} color="orange" />
        <KpiCard title="Flujo neto (12m)" value={totals.neto} prefix="$" isLoading={isLoading} color={totals.neto >= 0 ? "green" : "red"} />
      </SimpleGrid>

      <SectionCard title="Ingresos vs egresos por mes">
        {isLoading ? (
          <Skeleton height={280} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay movimientos de caja en el período." />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={rows} margin={RECHARTS_DEFAULTS.margin}>
              <CartesianGrid {...RECHARTS_DEFAULTS.gridStyle} />
              <XAxis dataKey="mes" {...RECHARTS_DEFAULTS.axisStyle} />
              <YAxis {...RECHARTS_DEFAULTS.axisStyle} tickFormatter={(v) => `$${Math.round(Number(v) / 1000)}k`} width={56} />
              <Tooltip contentStyle={RECHARTS_DEFAULTS.tooltipStyle} formatter={(v: number) => clp(Number(v))} />
              <Legend />
              <Bar dataKey="ingresos" name="Ingresos" fill={CHART_COLORS.success} radius={[4, 4, 0, 0]} />
              <Bar dataKey="egresos" name="Egresos" fill={CHART_COLORS.secondary} radius={[4, 4, 0, 0]} />
              <Line dataKey="neto" name="Neto" stroke={CHART_COLORS.primary} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <SectionCard title="Detalle mensual">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : (
          <Table.ScrollContainer minWidth={480}>
            <Table striped verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Mes</Table.Th>
                  <Table.Th ta="right">Ingresos</Table.Th>
                  <Table.Th ta="right">Egresos</Table.Th>
                  <Table.Th ta="right">Neto</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.periodo}>
                    <Table.Td>{r.periodo}</Table.Td>
                    <Table.Td ta="right">{clp(Number(r.ingresos))}</Table.Td>
                    <Table.Td ta="right">{clp(Number(r.egresos))}</Table.Td>
                    <Table.Td ta="right"><Text c={Number(r.neto) >= 0 ? "teal.7" : "red.7"}>{clp(Number(r.neto))}</Text></Table.Td>
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
