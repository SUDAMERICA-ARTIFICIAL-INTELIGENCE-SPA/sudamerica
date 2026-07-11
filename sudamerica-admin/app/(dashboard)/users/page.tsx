"use client";

import { useResetPassword, useUpdateUser, useUsers } from "@/hooks/useAdminUsers";
import {
  ActionIcon,
  Badge,
  Card,
  Group,
  Pagination,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconKey, IconSearch, IconUserOff } from "@tabler/icons-react";
import dayjs from "dayjs";
import { useState } from "react";

const ROLE_COLORS: Record<string, string> = {
  SUPERADMIN: "red",
  ADMIN: "indigo",
  ASESOR: "teal",
  VIEWER: "gray",
};

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useUsers({
    page,
    search: debouncedSearch || undefined,
    role: roleFilter || undefined,
  });
  const resetPwMutation = useResetPassword();
  const updateMutation = useUpdateUser();

  return (
    <Stack gap="lg">
      <Title order={2}>Usuarios</Title>

      <Group>
        <TextInput
          placeholder="Buscar por email..."
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => {
            setSearch(e.currentTarget.value);
            setPage(1);
          }}
          w={300}
        />
        <Select
          placeholder="Rol"
          data={[
            { value: "", label: "Todos" },
            { value: "SUPERADMIN", label: "SUPERADMIN" },
            { value: "ADMIN", label: "ADMIN" },
            { value: "ASESOR", label: "ASESOR" },
            { value: "VIEWER", label: "VIEWER" },
          ]}
          value={roleFilter}
          onChange={(v) => {
            setRoleFilter(v || null);
            setPage(1);
          }}
          clearable
          w={160}
        />
      </Group>

      <Card p={0}>
        {isLoading ? (
          <Stack p="md" gap="sm">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={`skel-${i.toString()}`} h={40} />
            ))}
          </Stack>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nombre</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th>Tenant</Table.Th>
                <Table.Th>Rol</Table.Th>
                <Table.Th>Creado</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Acciones</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.data.map((user) => (
                <Table.Tr key={user.id}>
                  <Table.Td fw={500}>{user.nombre} {user.apellido}</Table.Td>
                  <Table.Td>{user.email}</Table.Td>
                  <Table.Td>{user.tenant_nombre || "—"}</Table.Td>
                  <Table.Td>
                    <Badge color={ROLE_COLORS[user.role] || "gray"} variant="light">
                      {user.role}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{dayjs(user.created_at).format("DD/MM/YYYY")}</Table.Td>
                  <Table.Td>
                    <Badge color={user.activo ? "green" : "red"} variant="dot">
                      {user.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Tooltip label="Reset contraseña">
                        <ActionIcon
                          variant="subtle"
                          onClick={() => resetPwMutation.mutate(user.id)}
                          loading={resetPwMutation.isPending}
                        >
                          <IconKey size={16} />
                        </ActionIcon>
                      </Tooltip>
                      {user.activo && (
                        <Tooltip label="Desactivar">
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() =>
                              updateMutation.mutate({
                                id: user.id,
                                data: { activo: false },
                              })
                            }
                          >
                            <IconUserOff size={16} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      {data?.meta && data.meta.total_pages > 1 && (
        <Group justify="center">
          <Pagination
            total={data.meta.total_pages}
            value={page}
            onChange={setPage}
          />
        </Group>
      )}
    </Stack>
  );
}
