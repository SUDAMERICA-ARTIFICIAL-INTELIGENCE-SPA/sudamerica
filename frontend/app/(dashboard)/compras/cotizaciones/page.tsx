"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCotizaciones } from "@/hooks/useCompras";
import { Badge, Group, Pagination, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconFileDollar } from "@tabler/icons-react";
import { useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const ESTADO_COLOR: Record<string, string> = { RECIBIDA: "gray", SELECCIONADA: "green", RECHAZADA: "red" };

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useCotizaciones({ page, page_size: 20 });

  return (
    <Stack gap="lg">
      <PageHeader title="Cotizaciones" subtitle="Cotizaciones de proveedores y selección de ofertas" />

      <SectionCard title="Cotizaciones" subtitle={data ? `${data.meta.total} cotizaciones` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconFileDollar size={40} />} title="Sin cotizaciones" description="No hay cotizaciones registradas." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={800}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Validez</Table.Th>
                    <Table.Th ta="center">Líneas</Table.Th>
                    <Table.Th ta="right">Total</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td><Text ff="monospace">{c.numero}</Text></Table.Td>
                      <Table.Td>{c.proveedor_nombre ?? "—"}</Table.Td>
                      <Table.Td><Badge variant="light" color={ESTADO_COLOR[c.estado] ?? "gray"} radius="sm">{c.estado}</Badge></Table.Td>
                      <Table.Td>{fecha(c.fecha)}</Table.Td>
                      <Table.Td>{`${c.validez_dias} días`}</Table.Td>
                      <Table.Td ta="center">{c.items.length}</Table.Td>
                      <Table.Td ta="right">{clp(c.total)}</Table.Td>
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
