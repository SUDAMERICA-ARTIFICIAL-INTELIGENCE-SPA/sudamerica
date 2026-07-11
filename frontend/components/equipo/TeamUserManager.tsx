"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useSucursales } from "@/hooks/useSucursales";
import {
  useCreateUsuario,
  useDeactivateUsuario,
  useUpdateUsuarioRole,
  useUsuarios,
} from "@/hooks/useUsuarios";
import { useAuth } from "@/lib/auth";
import { USER_ROLE_COLORS, USER_ROLE_LABELS, UserRole } from "@/lib/enums";
import { rolesEquipo } from "@/lib/operativa";
import type { Usuario } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  PasswordInput,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconEdit, IconUserMinus, IconUserPlus } from "@tabler/icons-react";
import { useCallback, useMemo, useState } from "react";

interface InviteFormState {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  role: string;
  sucursal_id: string | null;
}

const INITIAL_INVITE: InviteFormState = {
  nombre: "",
  apellido: "",
  email: "",
  password: "",
  role: UserRole.PERSONAL,
  sucursal_id: null,
};

/** Max users per plan. Keys match TenantPlan enum values. */
const PLAN_MAX_USERS: Record<string, number> = {
  ESTANDAR: 3,
  FREE: 3,
  PLUS: 8,
  PRO: 15,
};

/** Roles that should be scoped to a sucursal */
const BRANCH_SCOPED_ROLES = new Set([
  UserRole.ADMIN,
  UserRole.PERSONAL,
  UserRole.ASESOR,
  UserRole.VIEWER,
]);

export function TeamUserManager() {
  const { user: currentUser } = useAuth();
  const rubro = useRubroLabels();
  const { data: usuarios, isLoading } = useUsuarios();
  const { data: sucursales } = useSucursales();
  const createUsuario = useCreateUsuario();
  const updateRole = useUpdateUsuarioRole();
  const deactivateUsuario = useDeactivateUsuario();

  const isSuperAdmin = currentUser?.role === UserRole.SUPERADMIN;
  const hasMultipleSucursales = (sucursales?.length ?? 0) > 1;

  const sucursalOptions = useMemo(() => {
    const opts = (sucursales ?? [])
      .filter((s) => s.activo)
      .map((s) => ({ value: s.id, label: s.nombre }));
    return [{ value: "", label: "Todas (admin global)" }, ...opts];
  }, [sucursales]);

  const sucursalMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of sucursales ?? []) map.set(s.id, s.nombre);
    return map;
  }, [sucursales]);

  const [inviteOpened, { open: openInvite, close: closeInvite }] = useDisclosure(false);
  const [roleOpened, { open: openRole, close: closeRole }] = useDisclosure(false);
  const [deactivateOpened, { open: openDeactivate, close: closeDeactivate }] = useDisclosure(false);

  const [inviteForm, setInviteForm] = useState<InviteFormState>(INITIAL_INVITE);
  const [selectedUser, setSelectedUser] = useState<Usuario | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>(UserRole.PERSONAL);

  const resetState = useCallback(() => {
    setInviteForm(INITIAL_INVITE);
    setSelectedUser(null);
    setSelectedRole(UserRole.PERSONAL);
  }, []);

  const showSucursalSelector =
    hasMultipleSucursales && BRANCH_SCOPED_ROLES.has(inviteForm.role as UserRole);

  const handleInvite = useCallback(() => {
    if (!inviteForm.nombre || !inviteForm.apellido || !inviteForm.email || !inviteForm.password)
      return;
    createUsuario.mutate(
      {
        nombre: inviteForm.nombre,
        apellido: inviteForm.apellido,
        email: inviteForm.email,
        password: inviteForm.password,
        role: inviteForm.role as UserRole,
        sucursal_id: inviteForm.sucursal_id || null,
      },
      {
        onSuccess: () => {
          resetState();
          closeInvite();
        },
      },
    );
  }, [inviteForm, createUsuario, resetState, closeInvite]);

  const handleRoleChange = useCallback(() => {
    if (!selectedUser) return;
    updateRole.mutate(
      { id: selectedUser.id, role: selectedRole as UserRole },
      {
        onSuccess: () => {
          resetState();
          closeRole();
        },
      },
    );
  }, [selectedUser, selectedRole, updateRole, resetState, closeRole]);

  const handleDeactivate = useCallback(() => {
    if (!selectedUser) return;
    deactivateUsuario.mutate(selectedUser.id, {
      onSuccess: () => {
        resetState();
        closeDeactivate();
      },
    });
  }, [selectedUser, deactivateUsuario, resetState, closeDeactivate]);

  const openRoleModal = useCallback(
    (u: Usuario) => {
      setSelectedUser(u);
      setSelectedRole(u.role);
      openRole();
    },
    [openRole],
  );

  const openDeactivateModal = useCallback(
    (u: Usuario) => {
      setSelectedUser(u);
      openDeactivate();
    },
    [openDeactivate],
  );

  if (isLoading) {
    return (
      <Paper p="lg" radius="md" withBorder>
        <Stack gap="md">
          <Skeleton height={28} width={200} />
          <Skeleton height={200} />
        </Stack>
      </Paper>
    );
  }

  const activeUsers = (usuarios ?? []).filter((u) => u.activo);
  const totalUsers = activeUsers.length;

  const maxUsersLabel = (() => {
    for (const [, max] of Object.entries(PLAN_MAX_USERS)) {
      if (totalUsers <= max) return `${totalUsers}/${max}`;
    }
    return `${totalUsers}`;
  })();

  // Solo roles aplicables al rubro del tenant (restaurante conserva el set actual completo).
  const rolesPermitidos = new Set<string>(rolesEquipo(rubro.key));
  const roleOptions = [
    ...(isSuperAdmin ? [{ value: UserRole.SUPERADMIN, label: "Super Administrador" }] : []),
    { value: UserRole.ADMIN, label: "Administrador" },
    { value: UserRole.PERSONAL, label: "Personal" },
  ].filter((option) => rolesPermitidos.has(option.value));

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString("es-CL", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <>
      <SectionCard
        title="Equipo"
        noBodyPadding
        action={
          <Group gap="sm" wrap="nowrap">
            <Badge variant="light" color="gray" size="lg">
              {maxUsersLabel} usuarios
            </Badge>
            {isSuperAdmin && (
              <Button
                leftSection={<IconUserPlus size={16} />}
                size="sm"
                onClick={() => {
                  resetState();
                  openInvite();
                }}
              >
                Invitar Usuario
              </Button>
            )}
          </Group>
        }
      >
        {activeUsers.length === 0 ? (
          <EmptyState icon="👥" title="No hay usuarios registrados." />
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nombre</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th>Rol</Table.Th>
                {hasMultipleSucursales && <Table.Th>Sucursal</Table.Th>}
                <Table.Th>Fecha de registro</Table.Th>
                {isSuperAdmin && <Table.Th style={{ width: 100 }}>Acciones</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {activeUsers.map((u) => (
                <Table.Tr key={u.id}>
                  <Table.Td fw={500}>
                    {u.nombre} {u.apellido}
                  </Table.Td>
                  <Table.Td>{u.email}</Table.Td>
                  <Table.Td>
                    <Badge variant="light" color={USER_ROLE_COLORS[u.role] ?? "gray"} size="sm">
                      {USER_ROLE_LABELS[u.role] ?? u.role}
                    </Badge>
                  </Table.Td>
                  {hasMultipleSucursales && (
                    <Table.Td>
                      {u.sucursal_id ? (
                        (sucursalMap.get(u.sucursal_id) ?? "—")
                      ) : (
                        <Text span fz="xs" c="dimmed">
                          Todas
                        </Text>
                      )}
                    </Table.Td>
                  )}
                  <Table.Td>{formatDate(u.created_at)}</Table.Td>
                  {isSuperAdmin && (
                    <Table.Td>
                      <Group gap={4}>
                        <Tooltip label="Cambiar rol" withArrow>
                          <ActionIcon
                            variant="subtle"
                            color="blue"
                            size="sm"
                            onClick={() => openRoleModal(u)}
                            aria-label={`Cambiar rol de ${u.nombre}`}
                            disabled={u.id === currentUser?.id}
                          >
                            <IconEdit size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Desactivar" withArrow>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            size="sm"
                            onClick={() => openDeactivateModal(u)}
                            aria-label={`Desactivar a ${u.nombre}`}
                            disabled={u.id === currentUser?.id}
                          >
                            <IconUserMinus size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </SectionCard>

      {/* Invite User Modal */}
      <Modal
        opened={inviteOpened}
        onClose={() => {
          resetState();
          closeInvite();
        }}
        title="Invitar Usuario"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Nombre"
            placeholder="Juan"
            required
            value={inviteForm.nombre}
            onChange={(e) =>
              setInviteForm((prev) => ({
                ...prev,
                nombre: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <TextInput
            label="Apellido"
            placeholder="Perez"
            required
            value={inviteForm.apellido}
            onChange={(e) =>
              setInviteForm((prev) => ({
                ...prev,
                apellido: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <TextInput
            label="Email"
            placeholder="juan@restaurante.cl"
            type="email"
            required
            value={inviteForm.email}
            onChange={(e) =>
              setInviteForm((prev) => ({
                ...prev,
                email: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <PasswordInput
            label="Contrasena"
            placeholder="Minimo 8 caracteres"
            required
            value={inviteForm.password}
            onChange={(e) =>
              setInviteForm((prev) => ({
                ...prev,
                password: e?.currentTarget?.value ?? "",
              }))
            }
          />
          <Select
            label="Rol"
            data={roleOptions}
            value={inviteForm.role}
            onChange={(val) =>
              setInviteForm((prev) => ({
                ...prev,
                role: val ?? UserRole.PERSONAL,
                sucursal_id: val === UserRole.SUPERADMIN ? null : prev.sucursal_id,
              }))
            }
            allowDeselect={false}
          />
          {showSucursalSelector && (
            <Select
              label="Sucursal"
              description="Asigna a una sucursal o deja 'Todas' para acceso global"
              data={sucursalOptions}
              value={inviteForm.sucursal_id ?? ""}
              onChange={(val) =>
                setInviteForm((prev) => ({
                  ...prev,
                  sucursal_id: val || null,
                }))
              }
              allowDeselect={false}
            />
          )}
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetState();
                closeInvite();
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleInvite}
              loading={createUsuario.isPending}
              disabled={
                !inviteForm.nombre ||
                !inviteForm.apellido ||
                !inviteForm.email ||
                !inviteForm.password
              }
            >
              Invitar
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Change Role Modal */}
      <Modal
        opened={roleOpened}
        onClose={() => {
          resetState();
          closeRole();
        }}
        title={`Cambiar rol de ${selectedUser?.nombre ?? ""}`}
        centered
        size="sm"
      >
        <Stack gap="md">
          <Select
            label="Nuevo rol"
            data={roleOptions}
            value={selectedRole}
            onChange={(val) => setSelectedRole(val ?? UserRole.PERSONAL)}
            allowDeselect={false}
          />
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetState();
                closeRole();
              }}
            >
              Cancelar
            </Button>
            <Button onClick={handleRoleChange} loading={updateRole.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Deactivate Confirmation Modal */}
      <Modal
        opened={deactivateOpened}
        onClose={() => {
          resetState();
          closeDeactivate();
        }}
        title="Confirmar Desactivacion"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text>
            Estas seguro de desactivar a{" "}
            <Text span fw={700}>
              {selectedUser?.nombre} {selectedUser?.apellido}
            </Text>
            ? El usuario perdera acceso al sistema.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={() => {
                resetState();
                closeDeactivate();
              }}
            >
              Cancelar
            </Button>
            <Button color="red" onClick={handleDeactivate} loading={deactivateUsuario.isPending}>
              Desactivar
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
