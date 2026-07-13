"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import { Badge, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { useMemo } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

export default function Page() {
  const { data, isLoading } = useProductos({ page: 1, page_size: 100 });

  const rows = useMemo(() => {
    return (data?.data ?? [])
      .map((p) => {
        const stock = Number(p.stock ?? 0);
        const costo = Number(p.costo ?? 0);
        const stockMin = Number(p.stock_minimo ?? 0);
        return {
          id: p.id,
          nombre: p.nombre,
          stock,
          costo,
          valor: stock * costo,
          bajoMinimo: stock <= stockMin,
        };
      })
      .sort((a, b) => b.valor - a.valor);
  }, [data]);

  const kpis = useMemo(() => {
    const valorTotal = rows.reduce((s, r) => s + r.valor, 0);
    const unidades = rows.reduce((s, r) => s + r.stock, 0);
    const bajoMinimo = rows.filter((r) => r.bajoMinimo).length;
    return { valorTotal, unidades, bajoMinimo };
  }, [rows]);

  return (
    <Stack gap="lg">
      <PageHeader title="Valorización" subtitle="Valor del inventario a costo por SKU" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Valor inventario" value={kpis.valorTotal} prefix="$" isLoading={isLoading} color="teal" />
        <KpiCard title="Unidades totales" value={kpis.unidades} isLoading={isLoading} color="blue" />
        <KpiCard title="SKUs bajo mínimo" value={kpis.bajoMinimo} isLoading={isLoading} color="orange" />
      </SimpleGrid>

      <SectionCard title="Valorización por producto" subtitle={data ? `${data.meta.total} productos` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : rows.length === 0 ? (
          <EmptyState title="Sin productos" description="No hay productos en el catálogo." />
        ) : (
          <Table.ScrollContainer minWidth={640}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Producto</Table.Th>
                  <Table.Th ta="right">Stock</Table.Th>
                  <Table.Th ta="right">Costo</Table.Th>
                  <Table.Th ta="right">Valor</Table.Th>
                  <Table.Th>Estado</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.nombre}</Table.Td>
                    <Table.Td ta="right">{r.stock}</Table.Td>
                    <Table.Td ta="right">{clp(r.costo)}</Table.Td>
                    <Table.Td ta="right">
                      <Text fw={600}>{clp(r.valor)}</Text>
                    </Table.Td>
                    <Table.Td>
                      {r.bajoMinimo ? (
                        <Badge variant="light" color="red" radius="sm">Bajo mínimo</Badge>
                      ) : (
                        <Badge variant="light" color="green" radius="sm">OK</Badge>
                      )}
                    </Table.Td>
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
