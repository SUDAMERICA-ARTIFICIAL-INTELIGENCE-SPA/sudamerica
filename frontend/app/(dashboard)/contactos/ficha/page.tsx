"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useLeads } from "@/hooks/useLeads";
import { useVentas } from "@/hooks/useVentas";
import { ClienteEstado, CLIENTE_ESTADO_COLORS, CLIENTE_ESTADO_LABELS } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import {
  Badge,
  Grid,
  Group,
  NavLink,
  ScrollArea,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconMail, IconPhone, IconSearch, IconUser } from "@tabler/icons-react";
import { useState } from "react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function fecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
}
function estadoColor(e: ClienteEstado | null) {
  return e ? (CLIENTE_ESTADO_COLORS[e] ?? "gray") : "gray";
}
function estadoLabel(e: ClienteEstado | null) {
  return e ? (CLIENTE_ESTADO_LABELS[e] ?? "—") : "—";
}

const ESTADO_OPTIONS = [
  { value: "", label: "Todos los estados" },
  ...Object.values(ClienteEstado).map((e) => ({ value: e, label: CLIENTE_ESTADO_LABELS[e] })),
];

export default function Page() {
  const [estado, setEstado] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useLeads({ page_size: 50, estado_cliente: estado });
  const clientes = data?.data ?? [];
  const filtered = clientes.filter((c) => c.nombre.toLowerCase().includes(search.toLowerCase()));
  const selected: Lead | null = filtered.find((c) => c.id === selectedId) ?? filtered[0] ?? null;

  const ventas = useVentas({ lead_id: selected?.id ?? "", page_size: 20 });
  const ventasRows = selected ? ventas.data?.data ?? [] : [];

  return (
    <Stack gap="lg">
      <PageHeader title="Ficha de cliente" subtitle="Vista 360° del cliente: contacto, valor, historial y segmentación" />

      <Grid gutter="lg">
        {/* Columna izquierda: lista + buscador */}
        <Grid.Col span={{ base: 12, md: 4 }}>
          <SectionCard title="Clientes">
            <Stack gap="sm">
              <TextInput
                leftSection={<IconSearch size={16} />}
                placeholder="Buscar por nombre…"
                value={search}
                onChange={(e) => setSearch(e.currentTarget.value)}
              />
              <Select
                data={ESTADO_OPTIONS}
                value={estado}
                onChange={(v) => {
                  setEstado(v ?? "");
                  setSelectedId(null);
                }}
                allowDeselect={false}
                aria-label="Filtrar por estado"
              />
              {isLoading ? (
                <Stack gap="xs">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
              ) : filtered.length === 0 ? (
                <EmptyState icon={<IconUser size={36} />} title="Sin clientes" description="No hay clientes que coincidan." />
              ) : (
                <ScrollArea.Autosize mah={520}>
                  <Stack gap={4}>
                    {filtered.map((c) => (
                      <NavLink
                        key={c.id}
                        active={selected?.id === c.id}
                        onClick={() => setSelectedId(c.id)}
                        label={<Text fw={500} size="sm">{c.nombre}</Text>}
                        description={
                          <Group gap="xs">
                            <Badge size="xs" variant="light" color={estadoColor(c.estado_cliente)} radius="sm">
                              {estadoLabel(c.estado_cliente)}
                            </Badge>
                            <Text size="xs" c="dimmed">{clp(Number(c.total_gastado))}</Text>
                          </Group>
                        }
                      />
                    ))}
                  </Stack>
                </ScrollArea.Autosize>
              )}
            </Stack>
          </SectionCard>
        </Grid.Col>

        {/* Columna derecha: ficha del seleccionado */}
        <Grid.Col span={{ base: 12, md: 8 }}>
          {!selected ? (
            <SectionCard>
              <EmptyState icon={<IconUser size={40} />} title="Selecciona un cliente" description="Elige un cliente de la lista para ver su ficha completa." />
            </SectionCard>
          ) : (
            <Stack gap="lg">
              <SectionCard
                title={selected.nombre}
                subtitle={estadoLabel(selected.estado_cliente)}
              >
                <SimpleGrid cols={{ base: 1, sm: 3 }}>
                  <KpiCard title="Total gastado" value={Number(selected.total_gastado)} prefix="$" color="teal" />
                  <KpiCard title="Pedidos" value={Number(selected.total_pedidos)} color="indigo" />
                  <KpiCard title="Score IA" value={selected.ai_score != null ? Number(selected.ai_score) : 0} color="grape" />
                </SimpleGrid>
              </SectionCard>

              <SectionCard title="Datos de contacto">
                <Stack gap="sm">
                  <Group gap="xs">
                    <IconPhone size={16} />
                    <Text size="sm">{selected.telefono ?? "—"}</Text>
                  </Group>
                  <Group gap="xs">
                    <IconMail size={16} />
                    <Text size="sm">{selected.email ?? "—"}</Text>
                  </Group>
                  <Group gap="lg">
                    <div>
                      <Text size="xs" c="dimmed">Canal</Text>
                      <Text size="sm">{selected.canal}</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Última visita</Text>
                      <Text size="sm">{fecha(selected.ultima_visita)}</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Favorito</Text>
                      <Text size="sm">{selected.plato_favorito ?? "—"}</Text>
                    </div>
                  </Group>
                  {selected.tags && selected.tags.length > 0 && (
                    <Group gap="xs">
                      {selected.tags.map((t) => (
                        <Badge key={t} variant="light" color="blue" radius="sm">{t}</Badge>
                      ))}
                    </Group>
                  )}
                </Stack>
              </SectionCard>

              <SectionCard title="Historial de compras">
                {ventas.isLoading ? (
                  <Skeleton height={120} radius="md" />
                ) : ventasRows.length === 0 ? (
                  <EmptyState title="Sin compras" description="Este cliente aún no registra ventas." />
                ) : (
                  <Table.ScrollContainer minWidth={360}>
                    <Table striped verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Fecha</Table.Th>
                          <Table.Th>Canal</Table.Th>
                          <Table.Th ta="right">Total</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {ventasRows.map((v) => (
                          <Table.Tr key={v.id}>
                            <Table.Td>{fecha(v.created_at)}</Table.Td>
                            <Table.Td>
                              {v.ai_assisted ? (
                                <Badge size="sm" variant="light" color="grape" radius="sm">Con IA</Badge>
                              ) : (
                                <Badge size="sm" variant="light" color="gray" radius="sm">Manual</Badge>
                              )}
                            </Table.Td>
                            <Table.Td ta="right">{clp(Number(v.total))}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Table.ScrollContainer>
                )}
              </SectionCard>
            </Stack>
          )}
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
