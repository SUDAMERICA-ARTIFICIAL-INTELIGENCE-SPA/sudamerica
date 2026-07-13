"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconAlertTriangle, IconPercentage } from "@tabler/icons-react";
import { useMemo, useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

type ProductoSku = Producto & { sku?: string | null };

function margenColor(pct: number) {
  if (pct >= 50) return "green";
  if (pct >= 30) return "yellow";
  return "red";
}

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useProductos({ page, page_size: 100 });

  const rows = useMemo(() => {
    const items = (data?.data ?? []) as ProductoSku[];
    return items
      .map((p) => {
        const precio = Number(p.precio) || 0;
        const costo = Number(p.costo ?? 0) || 0;
        const margen = precio - costo;
        const margenPct = precio > 0 ? (margen / precio) * 100 : 0;
        return { ...p, precioNum: precio, costoNum: costo, margen, margenPct };
      })
      .sort((a, b) => a.margenPct - b.margenPct);
  }, [data]);

  const margenPromedio = rows.length > 0 ? rows.reduce((s, r) => s + r.margenPct, 0) / rows.length : 0;
  const bajos = rows.filter((r) => r.margenPct < 30).length;

  return (
    <Stack gap="lg">
      <PageHeader title="Costos y márgenes" subtitle="Rentabilidad por producto: precio, costo y margen sobre el catálogo" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Margen promedio" value={margenPromedio} suffix="%" decimals={1} isLoading={isLoading} color="teal" icon={<IconPercentage size={18} />} />
        <KpiCard title="SKUs con margen bajo" value={bajos} isLoading={isLoading} color="red" icon={<IconAlertTriangle size={18} />} description="Margen bajo 30%" />
      </SimpleGrid>

      <SectionCard title="Márgenes por producto" subtitle={data ? `${data.meta.total} productos · ordenados por margen (peores primero)` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : rows.length === 0 ? (
          <EmptyState icon={<IconPercentage size={40} />} title="Sin productos" description="Aún no hay productos en el catálogo." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={720}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Producto</Table.Th>
                    <Table.Th ta="right">Precio</Table.Th>
                    <Table.Th ta="right">Costo</Table.Th>
                    <Table.Th ta="right">Margen</Table.Th>
                    <Table.Th ta="center">Margen %</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((r) => (
                    <Table.Tr key={r.id}>
                      <Table.Td>
                        <Text fw={500}>{r.nombre}</Text>
                        {r.sku ? <Text size="xs" c="dimmed" ff="monospace">{r.sku}</Text> : null}
                      </Table.Td>
                      <Table.Td ta="right">{clp(r.precioNum)}</Table.Td>
                      <Table.Td ta="right">{clp(r.costoNum)}</Table.Td>
                      <Table.Td ta="right">{clp(r.margen)}</Table.Td>
                      <Table.Td ta="center">
                        <Badge variant="light" color={margenColor(r.margenPct)} radius="sm">{r.margenPct.toFixed(1)}%</Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
            {data && data.meta.total_pages > 1 && (
              <Group justify="flex-end">
                <Pagination total={data.meta.total_pages} value={page} onChange={setPage} size="sm" radius="md" />
              </Group>
            )}
          </Stack>
        )}
      </SectionCard>
    </Stack>
  );
}
