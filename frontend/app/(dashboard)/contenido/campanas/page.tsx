"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCampanas } from "@/hooks/useOlab";
import { Badge, Group, Pagination, SimpleGrid, Skeleton, Stack, Table, Text } from "@mantine/core";
import { IconSend, IconSpeakerphone, IconTargetArrow } from "@tabler/icons-react";
import { useMemo, useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

const ESTADO_COLOR: Record<string, string> = {
  BORRADOR: "gray",
  PROGRAMADA: "blue",
  ACTIVA: "green",
  FINALIZADA: "gray",
};
const ESTADO_FALLBACK = "gray";

export default function Page() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useCampanas({ page, page_size: 50 });

  const totales = useMemo(() => {
    const rows = data?.data ?? [];
    return {
      activas: rows.filter((c) => c.estado === "ACTIVA").length,
      enviados: rows.reduce((s, c) => s + Number(c.enviados), 0),
      conversiones: rows.reduce((s, c) => s + Number(c.conversiones), 0),
      ingresos: rows.reduce((s, c) => s + Number(c.ingresos_generados), 0),
    };
  }, [data]);

  return (
    <Stack gap="lg">
      <PageHeader title="Campañas" subtitle="Campañas de marketing por canal: alcance, conversiones e ingresos generados" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Campañas activas" value={totales.activas} isLoading={isLoading} color="green" icon={<IconSpeakerphone size={18} />} />
        <KpiCard title="Enviados" value={totales.enviados} isLoading={isLoading} color="indigo" icon={<IconSend size={18} />} />
        <KpiCard title="Conversiones" value={totales.conversiones} isLoading={isLoading} color="grape" icon={<IconTargetArrow size={18} />} />
        <KpiCard title="Ingresos generados" value={totales.ingresos} prefix="$" isLoading={isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard title="Campañas" subtitle={data ? `${data.meta.total} campañas` : ""}>
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconSpeakerphone size={40} />} title="Sin campañas" description="Aún no hay campañas registradas." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={1000}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Campaña</Table.Th>
                    <Table.Th>Canal</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Segmento</Table.Th>
                    <Table.Th ta="right">Enviados</Table.Th>
                    <Table.Th ta="right">Abiertos</Table.Th>
                    <Table.Th ta="right">Conversiones</Table.Th>
                    <Table.Th ta="right">Ingresos</Table.Th>
                    <Table.Th ta="right">Presupuesto</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td><Text fw={500}>{c.nombre}</Text></Table.Td>
                      <Table.Td><Badge variant="light" color="cyan" radius="sm">{c.canal}</Badge></Table.Td>
                      <Table.Td>{c.tipo}</Table.Td>
                      <Table.Td><Badge variant="light" color={ESTADO_COLOR[c.estado] ?? ESTADO_FALLBACK} radius="sm">{c.estado}</Badge></Table.Td>
                      <Table.Td>{c.segmento ?? "—"}</Table.Td>
                      <Table.Td ta="right">{Number(c.enviados)}</Table.Td>
                      <Table.Td ta="right">{Number(c.abiertos)}</Table.Td>
                      <Table.Td ta="right">{Number(c.conversiones)}</Table.Td>
                      <Table.Td ta="right">{clp(Number(c.ingresos_generados))}</Table.Td>
                      <Table.Td ta="right">{clp(Number(c.presupuesto))}</Table.Td>
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
