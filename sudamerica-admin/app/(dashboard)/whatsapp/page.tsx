"use client";

import { useReconnectInstance, useWhatsAppInstances } from "@/hooks/useAdminWhatsApp";
import {
  ActionIcon,
  Badge,
  Card,
  Group,
  Pagination,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconPlugConnected, IconPlugConnectedX } from "@tabler/icons-react";
import { useState } from "react";

export default function WhatsAppPage() {
  const [page, setPage] = useState(1);
  const { data: instancesData, isLoading } = useWhatsAppInstances({ page });
  const reconnectMutation = useReconnectInstance();

  return (
    <Stack gap="lg">
      <Title order={2}>WhatsApp — Instancias</Title>

      <Card p={0}>
        {isLoading ? (
          <Stack p="md" gap="sm">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={`skel-${i.toString()}`} h={40} />
            ))}
          </Stack>
        ) : instancesData && instancesData.data.length > 0 ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Tenant</Table.Th>
                <Table.Th>Instancia</Table.Th>
                <Table.Th>Teléfono</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Acciones</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {instancesData.data.map((inst) => (
                <Table.Tr key={inst.id}>
                  <Table.Td>{inst.tenant_nombre || inst.tenant_id}</Table.Td>
                  <Table.Td fw={500}>{inst.instance_name}</Table.Td>
                  <Table.Td>{inst.phone || "—"}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={inst.status === "CONNECTED" ? "green" : "red"}
                      variant="light"
                      leftSection={
                        inst.status === "CONNECTED" ? (
                          <IconPlugConnected size={12} />
                        ) : (
                          <IconPlugConnectedX size={12} />
                        )
                      }
                    >
                      {inst.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {inst.status !== "CONNECTED" && (
                      <Tooltip label="Reconectar">
                        <ActionIcon
                          variant="subtle"
                          color="green"
                          onClick={() => reconnectMutation.mutate(inst.tenant_id)}
                          loading={reconnectMutation.isPending}
                        >
                          <IconPlugConnected size={16} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text p="xl" c="dimmed" ta="center">
            No hay instancias de WhatsApp configuradas.
          </Text>
        )}
      </Card>

      {instancesData?.meta && instancesData.meta.total_pages > 1 && (
        <Group justify="center">
          <Pagination
            total={instancesData.meta.total_pages}
            value={page}
            onChange={setPage}
          />
        </Group>
      )}
    </Stack>
  );
}
