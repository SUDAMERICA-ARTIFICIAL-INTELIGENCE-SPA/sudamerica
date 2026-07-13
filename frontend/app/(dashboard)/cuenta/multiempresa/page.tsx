"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useSucursales } from "@/hooks/useSucursales";
import { useTenant } from "@/hooks/useTenant";
import { Badge, Card, Group, Skeleton, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { IconBuilding, IconBuildingStore } from "@tabler/icons-react";

export default function Page() {
  const tenant = useTenant();
  const sucursales = useSucursales();

  const t = tenant.data;
  const lista = sucursales.data ?? [];
  const n = lista.length;

  return (
    <Stack gap="lg">
      <PageHeader
        title="Multiempresa"
        subtitle={n > 0 ? `Gestión de múltiples empresas (esta cuenta opera 1 empresa con ${n} sucursales)` : "Gestión de múltiples empresas"}
      />

      <SectionCard title="Empresa actual">
        {tenant.isLoading ? (
          <Skeleton height={90} radius="md" />
        ) : !t ? (
          <EmptyState icon={<IconBuilding size={40} />} title="Sin empresa" description="No se pudo cargar la información de la empresa." />
        ) : (
          <Card withBorder radius="md" padding="lg">
            <Group justify="space-between" align="flex-start">
              <Group gap="sm">
                <ThemeIcon variant="light" color="indigo" size="xl" radius="md"><IconBuilding size={24} /></ThemeIcon>
                <Stack gap={2}>
                  <Text fw={600} size="lg">{t.nombre}</Text>
                  {t.sector && <Text size="sm" c="dimmed">Rubro: {t.sector}</Text>}
                </Stack>
              </Group>
              <Badge variant="light" color="teal" radius="sm">Plan {t.plan}</Badge>
            </Group>
          </Card>
        )}
      </SectionCard>

      <SectionCard title="Sucursales" subtitle={n > 0 ? `${n} sucursales` : ""}>
        {sucursales.isLoading ? (
          <Stack gap="xs">{[0, 1, 2].map((i) => <Skeleton key={i} height={44} radius="sm" />)}</Stack>
        ) : lista.length === 0 ? (
          <EmptyState icon={<IconBuildingStore size={40} />} title="Sin sucursales" description="Esta empresa aún no tiene sucursales registradas." />
        ) : (
          <Table.ScrollContainer minWidth={560}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Sucursal</Table.Th>
                  <Table.Th>Ciudad</Table.Th>
                  <Table.Th>Región</Table.Th>
                  <Table.Th>Tipo</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {lista.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td><Text fw={500}>{s.nombre}</Text></Table.Td>
                    <Table.Td>{s.ciudad ?? "—"}</Table.Td>
                    <Table.Td>{s.region ?? "—"}</Table.Td>
                    <Table.Td>
                      {s.es_principal
                        ? <Badge variant="light" color="indigo" radius="sm">Principal</Badge>
                        : <Badge variant="outline" color="gray" radius="sm">Sucursal</Badge>}
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
