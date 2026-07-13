"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useMovimientos } from "@/hooks/useLentes";
import { Badge, Group, Pagination, SegmentedControl, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconArrowsExchange } from "@tabler/icons-react";
import { useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fechaHora(s: string) {
  return new Date(s).toLocaleString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Page() {
  const [page, setPage] = useState(1);
  const [tipo, setTipo] = useState("");
  const { data, isLoading } = useMovimientos({ page, page_size: 30, tipo });

  return (
    <Stack gap="lg">
      <PageHeader title="Movimientos" subtitle="Entradas por recepciones de compra · salidas por ventas" />

      <SectionCard
        title="Kardex"
        subtitle={data ? `${data.meta.total} movimientos` : ""}
        action={
          <SegmentedControl
            size="xs"
            value={tipo || "TODAS"}
            onChange={(v) => {
              setTipo(v === "TODAS" ? "" : v);
              setPage(1);
            }}
            data={["TODAS", "ENTRADA", "SALIDA"]}
          />
        }
      >
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconArrowsExchange size={40} />} title="Sin movimientos" description="No hay movimientos para este filtro." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={760}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Producto</Table.Th>
                    <Table.Th ta="right">Cantidad</Table.Th>
                    <Table.Th ta="right">Costo unitario</Table.Th>
                    <Table.Th>Referencia</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((m, i) => (
                    <Table.Tr key={`${m.producto_id ?? "x"}-${m.fecha}-${i}`}>
                      <Table.Td>
                        <Text size="sm" c="dimmed">{fechaHora(m.fecha)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge variant="light" color={m.tipo === "ENTRADA" ? "green" : "red"} radius="sm">
                          {m.tipo}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{m.producto ?? "—"}</Table.Td>
                      <Table.Td ta="right">{Number(m.cantidad)}</Table.Td>
                      <Table.Td ta="right">{m.costo_unitario != null ? clp(Number(m.costo_unitario)) : "—"}</Table.Td>
                      <Table.Td>{m.referencia ?? "—"}</Table.Td>
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
