"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useComandas } from "@/hooks/useComandas";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconTruckDelivery } from "@tabler/icons-react";
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
  PENDIENTE: { color: "yellow", label: "Pendiente" },
  EN_COCINA: { color: "orange", label: "En cocina" },
  EN_PROCESO: { color: "orange", label: "En proceso" },
  LISTO: { color: "blue", label: "Listo" },
  ENTREGADO: { color: "green", label: "Entregado" },
  CANCELADO: { color: "red", label: "Cancelado" },
};
const EN_CURSO = new Set(["PENDIENTE", "EN_COCINA", "EN_PROCESO", "LISTO"]);

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useComandas({ page, page_size: 20, tipo_entrega: "DELIVERY" });

  const enCurso = useMemo(
    () => (data?.data ?? []).filter((c) => EN_CURSO.has(c.estado)).length,
    [data],
  );

  return (
    <Stack gap="lg">
      <PageHeader title="Entregas" subtitle="Tablero de pedidos con despacho a domicilio (delivery)" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Entregas totales" value={data?.meta.total ?? 0} isLoading={isLoading} icon={<IconTruckDelivery size={18} />} />
        <KpiCard title="En curso (esta página)" value={enCurso} isLoading={isLoading} color="orange" />
      </SimpleGrid>

      <SectionCard title="Delivery" subtitle={data ? `${data.meta.total} entregas registradas` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconTruckDelivery size={40} />} title="Sin entregas" description="Aún no hay pedidos con despacho a domicilio." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={860}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Cliente</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Repartidor</Table.Th>
                    <Table.Th>Pago</Table.Th>
                    <Table.Th ta="right">Costo delivery</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((c) => {
                    const m = ESTADO_META[c.estado] ?? ESTADO_FALLBACK;
                    return (
                      <Table.Tr key={c.id}>
                        <Table.Td>
                          <Text fw={500}>{c.cliente_nombre ?? "—"}</Text>
                          {c.direccion_entrega && <Text size="xs" c="dimmed">{c.direccion_entrega}</Text>}
                        </Table.Td>
                        <Table.Td><Badge variant="light" color={m.color} radius="sm">{m.label}</Badge></Table.Td>
                        <Table.Td>{c.repartidor_nombre ?? "—"}</Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Text size="sm">{c.metodo_pago ?? "—"}</Text>
                            {c.pago_confirmado && <Badge variant="light" color="green" size="xs" radius="sm">Pagado</Badge>}
                          </Group>
                        </Table.Td>
                        <Table.Td ta="right">{c.costo_delivery > 0 ? clp(Number(c.costo_delivery)) : "—"}</Table.Td>
                        <Table.Td>{fecha(c.created_at)}</Table.Td>
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
