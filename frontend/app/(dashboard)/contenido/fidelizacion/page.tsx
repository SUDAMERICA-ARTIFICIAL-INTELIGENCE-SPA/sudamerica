"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useLoyaltyInsights, useSegmentacion } from "@/hooks/useLentes";
import { CHART_COLORS, RECHARTS_DEFAULTS } from "@/lib/chart-config";
import { Badge, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconCrown, IconUserExclamation } from "@tabler/icons-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

const ESTADO_COLOR: Record<string, string> = {
  VIP: "grape",
  FRECUENTE: "teal",
  ACTIVO: "green",
  NUEVO: "blue",
  EN_RIESGO: "orange",
  INACTIVO: "red",
};
const ESTADO_FALLBACK = "gray";

export default function Page() {
  const loyalty = useLoyaltyInsights();
  const segmentacion = useSegmentacion();

  const insights = loyalty.data;
  const segmentos = segmentacion.data ?? [];
  const enRiesgo = insights?.at_risk_customers ?? [];

  return (
    <Stack gap="lg">
      <PageHeader title="Fidelización" subtitle="Segmentación de clientes, VIPs frecuentes y clientes en riesgo de fuga" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="VIP frecuentes" value={insights?.total_vip_frecuente ?? 0} isLoading={loyalty.isLoading} color="grape" icon={<IconCrown size={18} />} />
        <KpiCard title="Clientes en riesgo" value={enRiesgo.length} isLoading={loyalty.isLoading} color="orange" icon={<IconUserExclamation size={18} />} />
      </SimpleGrid>

      <SectionCard title="Segmentos de clientes">
        {segmentacion.isLoading ? (
          <Skeleton height={280} radius="md" />
        ) : segmentos.length === 0 ? (
          <EmptyState title="Sin segmentos" description="Aún no hay datos de segmentación de clientes." />
        ) : (
          <Stack gap="lg">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={segmentos} margin={RECHARTS_DEFAULTS.margin}>
                <CartesianGrid {...RECHARTS_DEFAULTS.gridStyle} />
                <XAxis dataKey="segmento" {...RECHARTS_DEFAULTS.axisStyle} />
                <YAxis {...RECHARTS_DEFAULTS.axisStyle} width={40} />
                <Tooltip contentStyle={RECHARTS_DEFAULTS.tooltipStyle} formatter={(v: number) => `${Number(v)} clientes`} />
                <Bar dataKey="cantidad" name="Clientes" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <Table.ScrollContainer minWidth={480}>
              <Table striped verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Segmento</Table.Th>
                    <Table.Th ta="center">Clientes</Table.Th>
                    <Table.Th ta="right">Total gastado</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {segmentos.map((s) => (
                    <Table.Tr key={s.segmento}>
                      <Table.Td><Text fw={500}>{s.segmento}</Text></Table.Td>
                      <Table.Td ta="center">{Number(s.cantidad)}</Table.Td>
                      <Table.Td ta="right">{clp(Number(s.total_gastado))}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Stack>
        )}
      </SectionCard>

      <SectionCard title="Clientes en riesgo" subtitle={insights ? `${enRiesgo.length} clientes sin visitar hace tiempo` : ""}>
        {loyalty.isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : enRiesgo.length === 0 ? (
          <EmptyState icon={<IconUserExclamation size={40} />} title="Sin clientes en riesgo" description="No hay clientes marcados como en riesgo de fuga." />
        ) : (
          <Table.ScrollContainer minWidth={720}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Cliente</Table.Th>
                  <Table.Th>Estado</Table.Th>
                  <Table.Th ta="right">Total gastado</Table.Th>
                  <Table.Th ta="center">Días sin visita</Table.Th>
                  <Table.Th>Favorito</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {enRiesgo.map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td><Text fw={500}>{c.nombre}</Text></Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={ESTADO_COLOR[c.estado_cliente] ?? ESTADO_FALLBACK} radius="sm">{c.estado_cliente}</Badge>
                    </Table.Td>
                    <Table.Td ta="right">{clp(Number(c.total_gastado))}</Table.Td>
                    <Table.Td ta="center">{Number(c.dias_sin_visita)}</Table.Td>
                    <Table.Td>{c.plato_favorito ?? "—"}</Table.Td>
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
