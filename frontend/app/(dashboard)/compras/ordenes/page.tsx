"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useComprasResumen, useOrdenesCompra } from "@/hooks/useCompras";
import { Badge, Group, Pagination, SegmentedControl, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconClipboardList } from "@tabler/icons-react";
import { useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const ESTADO_COLOR: Record<string, string> = {
  BORRADOR: "gray",
  ENVIADA: "blue",
  CONFIRMADA: "indigo",
  RECIBIDA: "green",
  RECIBIDA_PARCIAL: "yellow",
  CANCELADA: "red",
};

export default function Page() {
  const [page, setPage] = useState(1);
  const [estado, setEstado] = useState("");
  const resumen = useComprasResumen();
  const { data, isLoading } = useOrdenesCompra({ page, page_size: 20, estado });
  const r = resumen.data;

  return (
    <Stack gap="lg">
      <PageHeader title="Órdenes de compra" subtitle="Órdenes emitidas a proveedores y su estado de recepción" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Órdenes abiertas" value={r?.ordenes_abiertas ?? 0} isLoading={resumen.isLoading} icon={<IconClipboardList size={18} />} />
        <KpiCard title="Órdenes del mes" value={r?.ordenes_mes ?? 0} isLoading={resumen.isLoading} color="indigo" />
        <KpiCard title="Comprado (12m)" value={r?.total_comprado_12m ?? 0} prefix="$" isLoading={resumen.isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard
        title="Órdenes"
        subtitle={data ? `${data.meta.total} órdenes` : ""}
        action={
          <SegmentedControl
            size="xs"
            value={estado || "TODAS"}
            onChange={(v) => { setEstado(v === "TODAS" ? "" : v); setPage(1); }}
            data={["TODAS", "BORRADOR", "ENVIADA", "CONFIRMADA", "RECIBIDA", "CANCELADA"]}
          />
        }
      >
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconClipboardList size={40} />} title="Sin órdenes" description="No hay órdenes de compra para este filtro." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={760}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Emisión</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th ta="center">Ítems</Table.Th>
                    <Table.Th ta="right">Total</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((o) => (
                    <Table.Tr key={o.id}>
                      <Table.Td><Text ff="monospace">{o.numero}</Text></Table.Td>
                      <Table.Td>{o.proveedor_nombre ?? "—"}</Table.Td>
                      <Table.Td>{fecha(o.fecha_emision)}</Table.Td>
                      <Table.Td><Badge variant="light" color={ESTADO_COLOR[o.estado] ?? "gray"} radius="sm">{o.estado}</Badge></Table.Td>
                      <Table.Td ta="center">{o.items_count}</Table.Td>
                      <Table.Td ta="right">{clp(o.total)}</Table.Td>
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
