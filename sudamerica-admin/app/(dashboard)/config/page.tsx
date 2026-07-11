"use client";

import { api } from "@/lib/api";
import type { ServiceHealth } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Group,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconRefresh } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";

export default function ConfigPage() {
  const {
    data: health,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["admin", "system", "health"],
    queryFn: () => api.get<{ services: ServiceHealth[] }>("/system/health"),
    refetchInterval: 60_000,
  });

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Configuración del sistema</Title>
        <Button
          variant="light"
          leftSection={<IconRefresh size={16} />}
          onClick={() => {
            void refetch();
            notifications.show({ title: "Actualizado", message: "", color: "blue" });
          }}
        >
          Actualizar
        </Button>
      </Group>

      <Card p="md">
        <Text fw={600} mb="md">
          Estado de servicios
        </Text>
        {isLoading ? (
          <Stack gap="sm">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={`skel-${i.toString()}`} h={40} />
            ))}
          </Stack>
        ) : (
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Servicio</Table.Th>
                <Table.Th>URL</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Latencia</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {health?.services.map((svc) => (
                <Table.Tr key={svc.name}>
                  <Table.Td fw={500}>{svc.name}</Table.Td>
                  <Table.Td>
                    <Text size="sm" ff="monospace">
                      {svc.url}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        svc.status === "healthy"
                          ? "green"
                          : svc.status === "unhealthy"
                            ? "yellow"
                            : "red"
                      }
                      variant="light"
                    >
                      {svc.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {svc.latency_ms !== null ? `${svc.latency_ms}ms` : "—"}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
