"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Badge, Card, Group, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { IconCoin, IconCurrencyDollar } from "@tabler/icons-react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}

type Moneda = { codigo: string; nombre: string; simbolo: string; referencia: number };
const REFERENCIA: Moneda[] = [
  { codigo: "USD", nombre: "Dólar estadounidense", simbolo: "US$", referencia: 950 },
  { codigo: "EUR", nombre: "Euro", simbolo: "€", referencia: 1030 },
  { codigo: "UF", nombre: "Unidad de Fomento", simbolo: "UF", referencia: 39000 },
];

export default function Page() {
  return (
    <Stack gap="lg">
      <PageHeader title="Monedas" subtitle="Configuración de moneda base y referencias de cambio" />

      <SectionCard title="Moneda base">
        <Card withBorder radius="md" padding="lg">
          <Group justify="space-between" align="flex-start">
            <Group gap="sm">
              <ThemeIcon variant="light" color="teal" size="xl" radius="md"><IconCurrencyDollar size={24} /></ThemeIcon>
              <Stack gap={2}>
                <Text fw={600} size="lg">CLP · Peso chileno</Text>
                <Text size="sm" c="dimmed">Ejemplo de formato: {clp(1990)}</Text>
              </Stack>
            </Group>
            <Badge variant="light" color="green" radius="sm">Activa</Badge>
          </Group>
        </Card>
      </SectionCard>

      <SectionCard
        title="Monedas de referencia"
        subtitle="Tipo de cambio referencial · valores aproximados, no se usan en transacciones"
      >
        <Table.ScrollContainer minWidth={520}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Código</Table.Th>
                <Table.Th>Moneda</Table.Th>
                <Table.Th>Símbolo</Table.Th>
                <Table.Th ta="right">Cambio referencial (CLP)</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {REFERENCIA.map((m) => (
                <Table.Tr key={m.codigo}>
                  <Table.Td>
                    <Group gap="xs">
                      <ThemeIcon variant="light" color="gray" size="sm" radius="sm"><IconCoin size={14} /></ThemeIcon>
                      <Text ff="monospace" fw={500}>{m.codigo}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>{m.nombre}</Table.Td>
                  <Table.Td>{m.simbolo}</Table.Td>
                  <Table.Td ta="right">{clp(m.referencia)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </SectionCard>
    </Stack>
  );
}
