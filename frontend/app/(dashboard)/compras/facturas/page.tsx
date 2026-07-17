"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useFacturasProveedor } from "@/hooks/useCompras";
import { Badge, Group, Pagination, SegmentedControl, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconFileInvoice } from "@tabler/icons-react";
import { useMemo, useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const ESTADO_COLOR: Record<string, string> = { PAGADA: "green", PENDIENTE: "yellow", VENCIDA: "red", ANULADA: "gray" };

export default function Page() {
  const [page, setPage] = useState(1);
  const [estado, setEstado] = useState("");
  const { data, isLoading } = useFacturasProveedor({ page, page_size: 20, estado });
  const cxp = useMemo(() => (data?.data ?? []).reduce((s, f) => s + Number(f.saldo), 0), [data]);

  return (
    <Stack gap="lg">
      <PageHeader title="Facturas de proveedor" subtitle="Documentos de compra y cuentas por pagar" />

      <SectionCard
        title="Facturas"
        subtitle={data ? `${data.meta.total} facturas · saldo por pagar en esta página ${clp(cxp)}` : ""}
        action={
          <SegmentedControl
            size="xs"
            value={estado || "TODAS"}
            onChange={(v) => { setEstado(v === "TODAS" ? "" : v); setPage(1); }}
            data={["TODAS", "PENDIENTE", "VENCIDA", "PAGADA"]}
          />
        }
      >
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconFileInvoice size={40} />} title="Sin facturas" description="No hay facturas para este filtro." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={760}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Folio</Table.Th>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Emisión</Table.Th>
                    <Table.Th>Vencimiento</Table.Th>
                    <Table.Th ta="right">Total</Table.Th>
                    <Table.Th ta="right">Saldo</Table.Th>
                    <Table.Th>Estado</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((f) => (
                    <Table.Tr key={f.id}>
                      <Table.Td><Text ff="monospace">{f.numero}</Text></Table.Td>
                      <Table.Td>{f.proveedor_nombre ?? "—"}</Table.Td>
                      <Table.Td>{fecha(f.fecha_emision)}</Table.Td>
                      <Table.Td>{fecha(f.fecha_vencimiento)}</Table.Td>
                      <Table.Td ta="right">{clp(f.total)}</Table.Td>
                      <Table.Td ta="right">{f.saldo > 0 ? clp(f.saldo) : "—"}</Table.Td>
                      <Table.Td><Badge variant="light" color={ESTADO_COLOR[f.estado] ?? "gray"} radius="sm">{f.estado}</Badge></Table.Td>
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
