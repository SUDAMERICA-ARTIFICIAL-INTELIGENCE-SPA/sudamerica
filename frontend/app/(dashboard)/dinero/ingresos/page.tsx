"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useFlujoCaja } from "@/hooks/useLentes";
import { CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import { SimpleGrid, Skeleton, Stack, Table } from "@mantine/core";
import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function mesLabel(periodo: string) {
  const [y, m] = periodo.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("es-CL", { month: "short" });
}

export default function Page() {
  const { data, isLoading } = useFlujoCaja(12);
  const rows = useMemo(
    () => (data ?? []).map((p) => ({ periodo: p.periodo, mes: mesLabel(p.periodo), ingresos: Number(p.ingresos) })),
    [data],
  );
  const kpis = useMemo(() => {
    const total = rows.reduce((s, r) => s + r.ingresos, 0);
    const mesActual = rows.length > 0 ? rows[rows.length - 1]!.ingresos : 0;
    const promedio = rows.length > 0 ? total / rows.length : 0;
    return { total, mesActual, promedio };
  }, [rows]);

  return (
    <Stack gap="lg">
      <PageHeader title="Ingresos" subtitle="Ingresos por ventas, últimos 12 meses" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Ingresos (12m)" value={kpis.total} prefix="$" isLoading={isLoading} color="teal" />
        <KpiCard title="Ingresos mes actual" value={kpis.mesActual} prefix="$" isLoading={isLoading} color="green" />
        <KpiCard title="Promedio mensual" value={kpis.promedio} prefix="$" isLoading={isLoading} color="blue" />
      </SimpleGrid>

      <SectionCard title="Ingresos por mes">
        {isLoading ? (
          <Skeleton height={280} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay ingresos registrados en el período." />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={rows} margin={RECHARTS_DEFAULTS.margin}>
              <defs>
                <linearGradient id="ingresosGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid {...RECHARTS_DEFAULTS.gridStyle} />
              <XAxis dataKey="mes" {...RECHARTS_DEFAULTS.axisStyle} />
              <YAxis {...RECHARTS_DEFAULTS.axisStyle} tickFormatter={(v) => `$${Math.round(Number(v) / 1000)}k`} width={56} />
              <Tooltip contentStyle={RECHARTS_DEFAULTS.tooltipStyle} formatter={(v: number) => clp(Number(v))} />
              <Area
                dataKey="ingresos"
                name="Ingresos"
                type="monotone"
                stroke={CHART_COLORS.success}
                strokeWidth={2}
                fill="url(#ingresosGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <SectionCard title="Detalle mensual">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : rows.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay ingresos registrados en el período." />
        ) : (
          <Table.ScrollContainer minWidth={360}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Periodo</Table.Th>
                  <Table.Th ta="right">Ingresos</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.periodo}>
                    <Table.Td>{r.periodo}</Table.Td>
                    <Table.Td ta="right">{clp(r.ingresos)}</Table.Td>
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
