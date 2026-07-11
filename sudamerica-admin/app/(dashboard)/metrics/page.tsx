"use client";

import {
  useMetricsOverview,
  useMetricsTimeseries,
  useTopTenants,
} from "@/hooks/useAdminMetrics";
import {
  Badge,
  Card,
  Grid,
  Group,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function MetricsPage() {
  const { data: overview, isLoading } = useMetricsOverview();
  const { data: timeseries } = useMetricsTimeseries(30);
  const { data: topTenants } = useTopTenants(10);

  return (
    <Stack gap="lg">
      <Title order={2}>Métricas de la plataforma</Title>

      {isLoading ? (
        <Grid>
          {Array.from({ length: 4 }).map((_, i) => (
            <Grid.Col key={`skel-${i.toString()}`} span={{ base: 12, sm: 6 }}>
              <Skeleton h={200} />
            </Grid.Col>
          ))}
        </Grid>
      ) : (
        <>
          <Grid>
            <Grid.Col span={{ base: 12, lg: 8 }}>
              <Card p="md">
                <Text fw={600} mb="md">
                  Leads por día
                </Text>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={timeseries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="leads" fill="#4C6EF5" radius={[4, 4, 0, 0]} name="Leads" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, lg: 4 }}>
              <Card p="md" h="100%">
                <Text fw={600} mb="md">
                  Resumen
                </Text>
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Text size="sm">Tenants totales</Text>
                    <Text fw={600}>{overview?.total_tenants}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Usuarios</Text>
                    <Text fw={600}>{overview?.total_users}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Leads este mes</Text>
                    <Text fw={600}>{overview?.total_leads_month}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">MRR</Text>
                    <Text fw={600} c="green">${overview?.mrr.toFixed(0)}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Conversaciones hoy</Text>
                    <Text fw={600}>{overview?.total_conversations_today}</Text>
                  </Group>
                </Stack>
              </Card>
            </Grid.Col>
          </Grid>

          <Card p="md">
            <Text fw={600} mb="md">
              Conversaciones por día
            </Text>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={timeseries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar
                  dataKey="conversations"
                  fill="#37B24D"
                  radius={[4, 4, 0, 0]}
                  name="Conversaciones"
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {topTenants && topTenants.length > 0 && (
            <Card p="md">
              <Text fw={600} mb="md">
                Top tenants por uso
              </Text>
              <Table striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    <Table.Th>Tenant</Table.Th>
                    <Table.Th>Plan</Table.Th>
                    <Table.Th>Leads</Table.Th>
                    <Table.Th>Conversaciones</Table.Th>
                    <Table.Th>Usuarios</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {topTenants.map((t, i) => (
                    <Table.Tr key={t.tenant_id}>
                      <Table.Td>{i + 1}</Table.Td>
                      <Table.Td fw={500}>{t.tenant_nombre}</Table.Td>
                      <Table.Td>
                        <Badge
                          color={t.plan === "PRO" ? "indigo" : "gray"}
                          variant="light"
                          size="sm"
                        >
                          {t.plan}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{t.leads}</Table.Td>
                      <Table.Td>{t.conversations}</Table.Td>
                      <Table.Td>{t.users}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          )}
        </>
      )}
    </Stack>
  );
}
