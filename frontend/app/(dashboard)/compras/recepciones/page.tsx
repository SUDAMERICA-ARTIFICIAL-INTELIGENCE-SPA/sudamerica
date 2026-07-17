"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useRecepciones } from "@/hooks/useCompras";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconTruckDelivery } from "@tabler/icons-react";
import { useState } from "react";

function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const ESTADO_COLOR: Record<string, string> = { COMPLETA: "green", PARCIAL: "yellow" };

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useRecepciones({ page, page_size: 20 });

  return (
    <Stack gap="lg">
      <PageHeader title="Recepciones" subtitle="Cada recepción ingresa stock al inventario" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Total recepciones" value={data?.meta.total ?? 0} isLoading={isLoading} icon={<IconTruckDelivery size={18} />} />
      </SimpleGrid>

      <SectionCard title="Recepciones" subtitle={data ? `${data.meta.total} recepciones` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconTruckDelivery size={40} />} title="Sin recepciones" description="Aún no se han registrado recepciones de mercadería." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={820}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Orden</Table.Th>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Recibido por</Table.Th>
                    <Table.Th ta="center">Ítems</Table.Th>
                    <Table.Th ta="right">Unidades</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((rec) => (
                    <Table.Tr key={rec.id}>
                      <Table.Td><Text ff="monospace">{rec.numero}</Text></Table.Td>
                      <Table.Td><Text ff="monospace">{rec.oc_numero ?? "—"}</Text></Table.Td>
                      <Table.Td>{rec.proveedor_nombre ?? "—"}</Table.Td>
                      <Table.Td>{fecha(rec.fecha)}</Table.Td>
                      <Table.Td><Badge variant="light" color={ESTADO_COLOR[rec.estado] ?? "gray"} radius="sm">{rec.estado}</Badge></Table.Td>
                      <Table.Td>{rec.recibido_por ?? "—"}</Table.Td>
                      <Table.Td ta="center">{rec.items_count}</Table.Td>
                      <Table.Td ta="right">{Number(rec.total_unidades)}</Table.Td>
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
