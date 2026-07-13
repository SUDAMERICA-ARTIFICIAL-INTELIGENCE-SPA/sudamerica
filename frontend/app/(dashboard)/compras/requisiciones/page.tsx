"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useRequisiciones } from "@/hooks/useCompras";
import { Badge, Group, Pagination, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconClipboardText } from "@tabler/icons-react";
import { useState } from "react";

function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const PRIORIDAD_COLOR: Record<string, string> = { ALTA: "red", MEDIA: "yellow", BAJA: "gray" };
const ESTADO_COLOR: Record<string, string> = { PENDIENTE: "yellow", APROBADA: "green", CONVERTIDA: "blue", RECHAZADA: "red" };

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useRequisiciones({ page, page_size: 20 });

  return (
    <Stack gap="lg">
      <PageHeader title="Requisiciones" subtitle="Solicitudes internas de compra pendientes de aprobación" />

      <SectionCard title="Requisiciones" subtitle={data ? `${data.meta.total} requisiciones` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconClipboardText size={40} />} title="Sin requisiciones" description="No hay solicitudes de compra registradas." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={780}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Solicitante</Table.Th>
                    <Table.Th>Prioridad</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Ítems</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((req) => {
                    const first = req.items[0];
                    const extra = req.items.length - 1;
                    return (
                      <Table.Tr key={req.id}>
                        <Table.Td><Text ff="monospace">{req.numero}</Text></Table.Td>
                        <Table.Td>{req.solicitante ?? "—"}</Table.Td>
                        <Table.Td><Badge variant="light" color={PRIORIDAD_COLOR[req.prioridad] ?? "gray"} radius="sm">{req.prioridad}</Badge></Table.Td>
                        <Table.Td><Badge variant="light" color={ESTADO_COLOR[req.estado] ?? "gray"} radius="sm">{req.estado}</Badge></Table.Td>
                        <Table.Td>{fecha(req.fecha)}</Table.Td>
                        <Table.Td>
                          {first ? (
                            <Text size="sm">{first.descripcion}{extra > 0 ? <Text span c="dimmed"> +{extra} más</Text> : null}</Text>
                          ) : "—"}
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
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
