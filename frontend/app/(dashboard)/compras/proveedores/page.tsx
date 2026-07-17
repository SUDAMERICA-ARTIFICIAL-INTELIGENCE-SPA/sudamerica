"use client";

import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useComprasResumen, useProveedores } from "@/hooks/useCompras";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text, TextInput } from "@mantine/core";
import { IconBuildingWarehouse, IconSearch } from "@tabler/icons-react";
import { useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

export default function Page() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const resumen = useComprasResumen();
  const { data, isLoading } = useProveedores({ page, page_size: 20, search });
  const r = resumen.data;

  return (
    <Stack gap="lg">
      <PageHeader title="Proveedores" subtitle="Directorio de proveedores, cuentas por pagar y actividad de compra" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Proveedores activos" value={r?.proveedores_activos ?? 0} isLoading={resumen.isLoading} icon={<IconBuildingWarehouse size={18} />} />
        <KpiCard title="Comprado (12m)" value={r?.total_comprado_12m ?? 0} prefix="$" isLoading={resumen.isLoading} color="teal" />
        <KpiCard title="Cuentas por pagar" value={r?.cxp_total ?? 0} prefix="$" isLoading={resumen.isLoading} color="orange" description={r ? `${clp(r.cxp_vencida)} vencida` : ""} />
        <KpiCard title="Órdenes abiertas" value={r?.ordenes_abiertas ?? 0} isLoading={resumen.isLoading} color="indigo" />
      </SimpleGrid>

      <SectionCard title="Proveedores" action={<TextInput leftSection={<IconSearch size={16} />} placeholder="Buscar…" value={search} onChange={(e) => { setSearch(e.currentTarget.value); setPage(1); }} maw={260} />}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconBuildingWarehouse size={40} />} title="Sin proveedores" description="Aún no hay proveedores registrados." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={720}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Categoría</Table.Th>
                    <Table.Th>Condición</Table.Th>
                    <Table.Th ta="right">Comprado</Table.Th>
                    <Table.Th ta="right">Por pagar</Table.Th>
                    <Table.Th ta="center">Órdenes</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td>
                        <Text fw={500}>{p.nombre}</Text>
                        {p.contacto_nombre && <Text size="xs" c="dimmed">{p.contacto_nombre}</Text>}
                      </Table.Td>
                      <Table.Td>{p.categoria ? <Badge variant="light" color="grape" radius="sm">{p.categoria}</Badge> : "—"}</Table.Td>
                      <Table.Td>{p.condicion_pago ?? "—"}</Table.Td>
                      <Table.Td ta="right">{clp(p.total_comprado)}</Table.Td>
                      <Table.Td ta="right">
                        {p.cxp > 0 ? <Text c="orange.7">{clp(p.cxp)}</Text> : clp(p.cxp)}
                      </Table.Td>
                      <Table.Td ta="center">{p.ordenes_count}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
            {data.meta.total_pages > 1 && (
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
