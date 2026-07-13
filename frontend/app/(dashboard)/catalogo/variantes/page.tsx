"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCategorias } from "@/hooks/useCategorias";
import { useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import { Badge, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconStack2 } from "@tabler/icons-react";
import { useMemo } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

type ProductoSku = Producto & { sku?: string | null };

const SIN_CATEGORIA = "__sin__";

export default function Page() {
  const { data, isLoading } = useProductos({ page: 1, page_size: 100 });
  const categorias = useCategorias();

  const nombreCategoria = useMemo(() => {
    const map: Record<string, string> = {};
    for (const c of categorias.data ?? []) map[c.id] = c.nombre;
    return map;
  }, [categorias.data]);

  const grupos = useMemo(() => {
    const items = ((data?.data ?? []) as ProductoSku[]).filter((p) => !(p.sku ?? "").startsWith("SERV-"));
    const byCat = new Map<string, ProductoSku[]>();
    for (const p of items) {
      const key = p.categoria_id ?? SIN_CATEGORIA;
      const arr = byCat.get(key) ?? [];
      arr.push(p);
      byCat.set(key, arr);
    }
    return Array.from(byCat.entries()).map(([catId, productos]) => ({
      catId,
      titulo: catId === SIN_CATEGORIA ? "Sin categoría" : (nombreCategoria[catId] ?? "Categoría"),
      productos,
    }));
  }, [data, nombreCategoria]);

  return (
    <Stack gap="lg">
      <PageHeader title="Variantes y presentaciones" subtitle="Presentaciones del catálogo por unidad de venta" />

      {isLoading ? (
        <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={48} radius="sm" />)}</Stack>
      ) : grupos.length === 0 ? (
        <SectionCard title="Presentaciones">
          <EmptyState icon={<IconStack2 size={40} />} title="Sin presentaciones" description="No hay productos en el catálogo." />
        </SectionCard>
      ) : (
        grupos.map((g) => (
          <SectionCard key={g.catId} title={g.titulo} subtitle={`${g.productos.length} presentaciones`}>
            <Table.ScrollContainer minWidth={640}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Presentación</Table.Th>
                    <Table.Th>SKU</Table.Th>
                    <Table.Th>Unidad</Table.Th>
                    <Table.Th ta="right">Precio</Table.Th>
                    <Table.Th ta="center">Stock</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {g.productos.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td><Text fw={500}>{p.nombre}</Text></Table.Td>
                      <Table.Td>{p.sku ? <Text size="xs" ff="monospace" c="dimmed">{p.sku}</Text> : "—"}</Table.Td>
                      <Table.Td><Badge variant="light" color="grape" radius="sm">{p.unidad_venta ?? "unidad"}</Badge></Table.Td>
                      <Table.Td ta="right">{clp(Number(p.precio))}</Table.Td>
                      <Table.Td ta="center">{Number(p.stock)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </SectionCard>
        ))
      )}
    </Stack>
  );
}
