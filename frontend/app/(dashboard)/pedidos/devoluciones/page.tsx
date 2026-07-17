"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useDevoluciones } from "@/hooks/useOlab";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconReceiptRefund } from "@tabler/icons-react";
import { useMemo, useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}

type EstadoMeta = { color: string; label: string };
const ESTADO_FALLBACK: EstadoMeta = { color: "gray", label: "—" };
const ESTADO_META: Record<string, EstadoMeta> = {
  SOLICITADA: { color: "yellow", label: "Solicitada" },
  APROBADA: { color: "blue", label: "Aprobada" },
  REEMBOLSADA: { color: "green", label: "Reembolsada" },
  RECHAZADA: { color: "red", label: "Rechazada" },
};

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useDevoluciones({ page, page_size: 20 });

  const montoReembolsado = useMemo(
    () => (data?.data ?? []).filter((d) => d.estado === "REEMBOLSADA").reduce((s, d) => s + Number(d.monto), 0),
    [data],
  );

  return (
    <Stack gap="lg">
      <PageHeader title="Devoluciones" subtitle="Solicitudes de devolución y reembolsos" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Devoluciones" value={data?.meta.total ?? 0} isLoading={isLoading} icon={<IconReceiptRefund size={18} />} />
        <KpiCard title="Reembolsado (esta página)" value={montoReembolsado} prefix="$" isLoading={isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard title="Solicitudes" subtitle={data ? `${data.meta.total} devoluciones registradas` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconReceiptRefund size={40} />} title="Sin devoluciones" description="Aún no hay solicitudes de devolución." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={820}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Cliente</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Motivo</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Reembolso</Table.Th>
                    <Table.Th ta="right">Monto</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((d) => {
                    const m = ESTADO_META[d.estado] ?? ESTADO_FALLBACK;
                    return (
                      <Table.Tr key={d.id}>
                        <Table.Td><Text ff="monospace">{d.numero}</Text></Table.Td>
                        <Table.Td>{d.cliente_nombre ?? "—"}</Table.Td>
                        <Table.Td>{fecha(d.fecha)}</Table.Td>
                        <Table.Td><Badge variant="light" color="grape" radius="sm">{d.motivo}</Badge></Table.Td>
                        <Table.Td><Badge variant="light" color={m.color} radius="sm">{m.label}</Badge></Table.Td>
                        <Table.Td>{d.metodo_reembolso ?? "—"}</Table.Td>
                        <Table.Td ta="right">{clp(Number(d.monto))}</Table.Td>
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
