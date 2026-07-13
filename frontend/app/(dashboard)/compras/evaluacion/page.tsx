"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useEvaluacionProveedores } from "@/hooks/useCompras";
import { Badge, Group, Progress, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconStar } from "@tabler/icons-react";
import { useMemo } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

export default function Page() {
  const { data, isLoading } = useEvaluacionProveedores();
  const rows = useMemo(
    () => [...(data ?? [])].sort((a, b) => Number(b.total_comprado) - Number(a.total_comprado)),
    [data],
  );
  const puntualidadProm = useMemo(() => {
    if (!data || data.length === 0) return 0;
    return data.reduce((s, p) => s + Number(p.puntualidad_pct), 0) / data.length;
  }, [data]);

  return (
    <Stack gap="lg">
      <PageHeader title="Evaluación de proveedores" subtitle="Desempeño de proveedores: cumplimiento, puntualidad y volumen" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Proveedores evaluados" value={data?.length ?? 0} isLoading={isLoading} icon={<IconStar size={18} />} />
        <KpiCard title="Puntualidad promedio" value={puntualidadProm} suffix="%" decimals={0} isLoading={isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard title="Ranking de proveedores">
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.length === 0 ? (
          <EmptyState icon={<IconStar size={40} />} title="Sin evaluaciones" description="Aún no hay datos de desempeño de proveedores." />
        ) : (
          <Table.ScrollContainer minWidth={900}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Proveedor</Table.Th>
                  <Table.Th>Categoría</Table.Th>
                  <Table.Th>Rating</Table.Th>
                  <Table.Th ta="center">Órdenes</Table.Th>
                  <Table.Th ta="center">Recibidas</Table.Th>
                  <Table.Th>Cumplimiento</Table.Th>
                  <Table.Th ta="right">Puntualidad</Table.Th>
                  <Table.Th ta="right">Lead time</Table.Th>
                  <Table.Th ta="right">Comprado</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((p) => (
                  <Table.Tr key={p.proveedor_id}>
                    <Table.Td><Text fw={500}>{p.nombre}</Text></Table.Td>
                    <Table.Td>{p.categoria ? <Badge variant="light" color="grape" radius="sm">{p.categoria}</Badge> : "—"}</Table.Td>
                    <Table.Td>{`⭐ ${Number(p.rating).toFixed(1)}`}</Table.Td>
                    <Table.Td ta="center">{p.ordenes_totales}</Table.Td>
                    <Table.Td ta="center">{p.ordenes_recibidas}</Table.Td>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text size="xs" c="dimmed">{`${Number(p.cumplimiento_pct).toFixed(0)}%`}</Text>
                        <Progress value={Number(p.cumplimiento_pct)} size="sm" radius="xl" />
                      </Stack>
                    </Table.Td>
                    <Table.Td ta="right">{`${Number(p.puntualidad_pct).toFixed(0)}%`}</Table.Td>
                    <Table.Td ta="right">{p.lead_time_dias != null ? `${Number(p.lead_time_dias)} días` : "—"}</Table.Td>
                    <Table.Td ta="right">{clp(Number(p.total_comprado))}</Table.Td>
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
