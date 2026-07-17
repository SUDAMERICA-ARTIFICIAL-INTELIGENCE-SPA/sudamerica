"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useDocumentos } from "@/hooks/useOlab";
import { Badge, Group, Pagination, SegmentedControl, SimpleGrid, Skeleton, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import {
  IconFile,
  IconFileInvoice,
  IconFileSpreadsheet,
  IconFileText,
  IconPhoto,
  IconReceipt,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useState } from "react";

function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}

type TipoMeta = { color: string; icon: ReactNode };
const TIPO_FALLBACK: TipoMeta = { color: "gray", icon: <IconFile size={18} /> };
const TIPO_META: Record<string, TipoMeta> = {
  FACTURA: { color: "blue", icon: <IconFileInvoice size={18} /> },
  CONTRATO: { color: "violet", icon: <IconFileText size={18} /> },
  BOLETA: { color: "cyan", icon: <IconReceipt size={18} /> },
  IMAGEN: { color: "grape", icon: <IconPhoto size={18} /> },
  PLANILLA: { color: "teal", icon: <IconFileSpreadsheet size={18} /> },
  OTRO: { color: "gray", icon: <IconFile size={18} /> },
};

export default function Page() {
  const [page, setPage] = useState(1);
  const [tipo, setTipo] = useState("");
  const { data, isLoading } = useDocumentos({ page, page_size: 50, tipo });

  return (
    <Stack gap="lg">
      <PageHeader title="Archivos" subtitle="Documentos y archivos adjuntos de la empresa" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Documentos" value={data?.meta.total ?? 0} isLoading={isLoading} icon={<IconFile size={18} />} />
      </SimpleGrid>

      <SectionCard
        title="Archivos"
        action={
          <SegmentedControl
            size="xs"
            value={tipo || "TODOS"}
            onChange={(v) => { setTipo(v === "TODOS" ? "" : v); setPage(1); }}
            data={["TODOS", "FACTURA", "CONTRATO", "BOLETA", "IMAGEN", "PLANILLA", "OTRO"]}
          />
        }
      >
        {isLoading ? (
          <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : !data || data.data.length === 0 ? (
          <EmptyState icon={<IconFile size={40} />} title="Sin documentos" description="No hay archivos para este filtro." />
        ) : (
          <Stack gap="md">
            <Table.ScrollContainer minWidth={820}>
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Categoría</Table.Th>
                    <Table.Th>Subido por</Table.Th>
                    <Table.Th ta="right">Tamaño</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.data.map((d) => {
                    const m = TIPO_META[d.tipo] ?? TIPO_FALLBACK;
                    return (
                      <Table.Tr key={d.id}>
                        <Table.Td>
                          <Group gap="sm">
                            <ThemeIcon variant="light" color={m.color} size="md" radius="sm">{m.icon}</ThemeIcon>
                            <Text fw={500}>{d.nombre}</Text>
                          </Group>
                        </Table.Td>
                        <Table.Td><Badge variant="light" color={m.color} radius="sm">{d.tipo}</Badge></Table.Td>
                        <Table.Td>{d.categoria ?? "—"}</Table.Td>
                        <Table.Td>{d.subido_por ?? "—"}</Table.Td>
                        <Table.Td ta="right">{d.tamano_kb != null ? `${d.tamano_kb} KB` : "—"}</Table.Td>
                        <Table.Td>{fecha(d.created_at)}</Table.Td>
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
