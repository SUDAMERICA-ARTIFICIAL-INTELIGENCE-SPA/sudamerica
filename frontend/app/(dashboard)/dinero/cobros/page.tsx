"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCobros } from "@/hooks/useLentes";
import { Badge, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
const ESTADO_COLOR: Record<string, string> = {
  PENDIENTE: "yellow",
  PAGADO: "green",
  COBRADO: "green",
  ANULADO: "gray",
  VENCIDO: "red",
};

export default function Page() {
  const { data, isLoading } = useCobros();

  return (
    <Stack gap="lg">
      <PageHeader title="Cobros y pagos" subtitle="Cobros recibidos y montos pendientes por pedido" />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <KpiCard title="Total cobrado" value={Number(data?.total_cobrado ?? 0)} prefix="$" isLoading={isLoading} color="teal" />
        <KpiCard title="Total pendiente" value={Number(data?.total_pendiente ?? 0)} prefix="$" isLoading={isLoading} color="orange" />
        <KpiCard title="Pedidos pendientes" value={Number(data?.pedidos_pendientes ?? 0)} isLoading={isLoading} color="blue" />
      </SimpleGrid>

      <SectionCard title="Por medio de pago">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : !data || data.por_metodo.length === 0 ? (
          <EmptyState title="Sin datos" description="No hay cobros registrados por medio de pago." />
        ) : (
          <Table.ScrollContainer minWidth={520}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Medio de pago</Table.Th>
                  <Table.Th ta="right">Cobrado</Table.Th>
                  <Table.Th ta="right">Pendiente</Table.Th>
                  <Table.Th ta="right">Pedidos</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.por_metodo.map((m) => (
                  <Table.Tr key={m.metodo}>
                    <Table.Td>{m.metodo}</Table.Td>
                    <Table.Td ta="right">{clp(Number(m.cobrado))}</Table.Td>
                    <Table.Td ta="right">{Number(m.pendiente) > 0 ? clp(Number(m.pendiente)) : "—"}</Table.Td>
                    <Table.Td ta="right">{Number(m.pedidos)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </SectionCard>

      <SectionCard title="Pendientes recientes">
        {isLoading ? (
          <Skeleton height={160} radius="md" />
        ) : !data || data.pendientes_recientes.length === 0 ? (
          <EmptyState title="Sin pendientes" description="No hay cobros pendientes recientes." />
        ) : (
          <Table.ScrollContainer minWidth={620}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Cliente</Table.Th>
                  <Table.Th ta="right">Monto</Table.Th>
                  <Table.Th>Medio</Table.Th>
                  <Table.Th>Estado</Table.Th>
                  <Table.Th>Fecha</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.pendientes_recientes.map((p) => (
                  <Table.Tr key={p.comanda_id}>
                    <Table.Td>{p.cliente ?? "—"}</Table.Td>
                    <Table.Td ta="right">{clp(Number(p.monto))}</Table.Td>
                    <Table.Td>{p.metodo ?? "—"}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={ESTADO_COLOR[p.estado] ?? "gray"} radius="sm">
                        {p.estado}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">{fecha(p.fecha)}</Text>
                    </Table.Td>
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
