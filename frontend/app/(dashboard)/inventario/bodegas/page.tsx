"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useProductos } from "@/hooks/useProductos";
import { useSucursales } from "@/hooks/useSucursales";
import { Badge, Group, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconBuildingWarehouse } from "@tabler/icons-react";
import { useMemo } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

export default function Page() {
  const { data: sucursales, isLoading: loadingSuc } = useSucursales();
  const { data: productos, isLoading: loadingProd } = useProductos({ page: 1, page_size: 100 });
  const isLoading = loadingSuc || loadingProd;

  const rows = useMemo(() => {
    return (productos?.data ?? []).map((p) => {
      const stock = Number(p.stock ?? 0);
      const costo = Number(p.costo ?? 0);
      return { id: p.id, nombre: p.nombre, stock, valor: stock * costo };
    });
  }, [productos]);

  const totales = useMemo(() => {
    const skus = rows.length;
    const unidades = rows.reduce((s, r) => s + r.stock, 0);
    const valor = rows.reduce((s, r) => s + r.valor, 0);
    return { skus, unidades, valor };
  }, [rows]);

  const bodegas = sucursales ?? [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Bodegas"
        subtitle="Vista consolidada: el stock del catálogo es global, no está repartido por bodega"
      />

      {isLoading ? (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {[0, 1, 2].map((i) => <Skeleton key={i} height={140} radius="md" />)}
        </SimpleGrid>
      ) : bodegas.length === 0 ? (
        <EmptyState icon={<IconBuildingWarehouse size={40} />} title="Sin bodegas" description="No hay sucursales/bodegas registradas." />
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {bodegas.map((b) => (
            <SectionCard
              key={b.id}
              title={b.nombre}
              subtitle={[b.ciudad, b.region].filter(Boolean).join(", ") || "—"}
            >
              <Stack gap="sm">
                {b.es_principal && (
                  <Badge variant="light" color="blue" radius="sm" w="fit-content">Principal</Badge>
                )}
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">SKUs</Text>
                  <Text fw={600}>{totales.skus}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Unidades</Text>
                  <Text fw={600}>{totales.unidades}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Valor aprox.</Text>
                  <Text fw={600}>{clp(totales.valor)}</Text>
                </Group>
                <Text size="xs" c="dimmed">Cifras consolidadas del catálogo (sin reparto por bodega).</Text>
              </Stack>
            </SectionCard>
          ))}
        </SimpleGrid>
      )}

      <SectionCard title="Productos con stock" subtitle="Stock total del catálogo (vista consolidada)">
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : rows.length === 0 ? (
          <EmptyState title="Sin productos" description="No hay productos en el catálogo." />
        ) : (
          <Table.ScrollContainer minWidth={480}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Producto</Table.Th>
                  <Table.Th ta="right">Stock</Table.Th>
                  <Table.Th ta="right">Valor</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.nombre}</Table.Td>
                    <Table.Td ta="right">{r.stock}</Table.Td>
                    <Table.Td ta="right">{clp(r.valor)}</Table.Td>
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
