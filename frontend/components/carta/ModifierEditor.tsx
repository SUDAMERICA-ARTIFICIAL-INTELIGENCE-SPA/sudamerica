"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import {
  useCreateModifierGroup,
  useDeleteModifierGroup,
  useModifierGroups,
  useUpdateModifierGroup,
} from "@/hooks/useModifiers";
import type { CreateModifierDto } from "@/hooks/useModifiers";
import { ModifierGroupTipo } from "@/lib/enums";
import type { ModifierGroup } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Select,
  Skeleton,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useEffect, useState } from "react";

interface InlineModifier {
  nombre: string;
  precio_delta: number;
}

interface GroupFormValues {
  nombre: string;
  tipo: string;
  obligatorio: boolean;
  max_selecciones: string;
  modifiers: InlineModifier[];
}

function ModifierGroupForm({
  opened,
  onClose,
  group,
}: {
  opened: boolean;
  onClose: () => void;
  group: ModifierGroup | null;
}) {
  const isEdit = !!group;
  const { mutate: create, isPending: creating } = useCreateModifierGroup();
  const { mutate: update, isPending: updating } = useUpdateModifierGroup();

  const form = useForm<GroupFormValues>({
    initialValues: {
      nombre: "",
      tipo: ModifierGroupTipo.MULTI_SELECT,
      obligatorio: false,
      max_selecciones: "",
      modifiers: [{ nombre: "", precio_delta: 0 }],
    },
    validate: {
      nombre: (v) => (v.trim().length < 2 ? "Mínimo 2 caracteres" : null),
    },
  });

  useEffect(() => {
    if (group) {
      form.setValues({
        nombre: group.nombre,
        tipo: group.tipo,
        obligatorio: group.obligatorio,
        max_selecciones: group.max_selecciones?.toString() ?? "",
        modifiers: group.modifiers.map((m) => ({
          nombre: m.nombre,
          precio_delta: m.precio_delta,
        })),
      });
    } else {
      form.reset();
    }
  }, [group, opened]);

  function addModifier() {
    form.insertListItem("modifiers", { nombre: "", precio_delta: 0 });
  }

  function removeModifier(index: number) {
    form.removeListItem("modifiers", index);
  }

  function handleSubmit(values: GroupFormValues) {
    const validModifiers: CreateModifierDto[] = values.modifiers
      .filter((m) => m.nombre.trim().length > 0)
      .map((m, i) => ({
        nombre: m.nombre.trim(),
        precio_delta: m.precio_delta,
        orden: i,
      }));

    if (isEdit) {
      update(
        {
          id: group.id,
          dto: {
            nombre: values.nombre.trim(),
            tipo: values.tipo,
            obligatorio: values.obligatorio,
            max_selecciones: values.max_selecciones ? Number(values.max_selecciones) : null,
          },
        },
        { onSuccess: onClose },
      );
    } else {
      create(
        {
          nombre: values.nombre.trim(),
          tipo: values.tipo,
          obligatorio: values.obligatorio,
          max_selecciones: values.max_selecciones ? Number(values.max_selecciones) : undefined,
          modifiers: validModifiers.length > 0 ? validModifiers : undefined,
        },
        { onSuccess: onClose },
      );
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? "Editar Grupo de Modificadores" : "Nuevo Grupo de Modificadores"}
      size="lg"
      radius="md"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Nombre del grupo"
            placeholder='Ej: "Extras", "Quitar ingrediente", "Tamaño"'
            required
            radius="md"
            aria-label="Nombre del grupo"
            {...form.getInputProps("nombre")}
          />

          <Group grow gap="sm">
            <Select
              label="Tipo de selección"
              data={[
                { value: ModifierGroupTipo.SINGLE_SELECT, label: "Selección única" },
                { value: ModifierGroupTipo.MULTI_SELECT, label: "Selección múltiple" },
              ]}
              radius="md"
              aria-label="Tipo de selección"
              {...form.getInputProps("tipo")}
            />
            <NumberInput
              label="Máx. selecciones"
              placeholder="Sin límite"
              min={1}
              radius="md"
              aria-label="Máximo de selecciones"
              {...form.getInputProps("max_selecciones")}
            />
          </Group>

          <Switch
            label="Obligatorio"
            description="El cliente debe elegir al menos una opción"
            {...form.getInputProps("obligatorio", { type: "checkbox" })}
          />

          {!isEdit && (
            <>
              <Title order={5}>Opciones del modificador</Title>
              {form.values.modifiers.map((_, index) => (
                <Group key={`mod-${index}`} gap="sm" wrap="nowrap">
                  <TextInput
                    placeholder="Ej: Extra queso"
                    style={{ flex: 1 }}
                    radius="md"
                    aria-label={`Nombre opción ${index + 1}`}
                    {...form.getInputProps(`modifiers.${index}.nombre`)}
                  />
                  <NumberInput
                    placeholder="+$0"
                    prefix="$"
                    w={120}
                    radius="md"
                    aria-label={`Precio delta opción ${index + 1}`}
                    {...form.getInputProps(`modifiers.${index}.precio_delta`)}
                  />
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={() => removeModifier(index)}
                    aria-label={`Eliminar opción ${index + 1}`}
                    disabled={form.values.modifiers.length <= 1}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Group>
              ))}
              <Button
                variant="subtle"
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={addModifier}
                aria-label="Agregar opción"
              >
                Agregar opción
              </Button>
            </>
          )}

          <Group justify="flex-end" gap="sm" mt="xs">
            <Button variant="subtle" color="gray" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={creating || updating} color="indigo" radius="md">
              {isEdit ? "Guardar Cambios" : "Crear Grupo"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function ModifierEditor() {
  const { data, isLoading } = useModifierGroups({ page: 1, page_size: 100 });
  const { mutate: deleteGroup } = useDeleteModifierGroup();
  const [formOpened, setFormOpened] = useState(false);
  const [editing, setEditing] = useState<ModifierGroup | null>(null);

  const groups = data?.data ?? [];

  function handleEdit(group: ModifierGroup) {
    setEditing(group);
    setFormOpened(true);
  }

  function handleDelete(group: ModifierGroup) {
    modals.openConfirmModal({
      title: "Eliminar grupo de modificadores",
      children: (
        <Text fz={14}>¿Eliminar el grupo &quot;{group.nombre}&quot; y todas sus opciones?</Text>
      ),
      labels: { confirm: "Eliminar", cancel: "Cancelar" },
      confirmProps: { color: "red" },
      onConfirm: () => deleteGroup(group.id),
    });
  }

  function handleClose() {
    setFormOpened(false);
    setEditing(null);
  }

  return (
    <Stack gap="lg">
      <SectionCard
        title="Modificadores"
        action={
          <Button
            leftSection={<IconPlus size={16} />}
            color="indigo"
            onClick={() => {
              setEditing(null);
              setFormOpened(true);
            }}
            radius="md"
            aria-label="Crear grupo de modificadores"
          >
            Nuevo Grupo
          </Button>
        }
      >
        {isLoading ? (
          <Stack gap="sm">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={`skel-${i}`} height={80} radius="md" />
            ))}
          </Stack>
        ) : groups.length === 0 ? (
          <EmptyState title='No hay grupos de modificadores. Crea uno para agregar opciones como "Extra queso" o "Sin cebolla" a tus platos.' />
        ) : (
          <Stack gap="sm">
            {groups.map((group) => (
              <Card key={group.id} radius="md" p="sm" withBorder>
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <Text fw={600}>{group.nombre}</Text>
                    <Badge size="xs" variant="light" color="blue">
                      {group.tipo === "SINGLE_SELECT" ? "Única" : "Múltiple"}
                    </Badge>
                    {group.obligatorio && (
                      <Badge size="xs" variant="light" color="red">
                        Obligatorio
                      </Badge>
                    )}
                  </Group>
                  <Group gap={4}>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      onClick={() => handleEdit(group)}
                      aria-label={`Editar ${group.nombre}`}
                    >
                      <IconEdit size={14} />
                    </ActionIcon>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={() => handleDelete(group)}
                      aria-label={`Eliminar ${group.nombre}`}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Group>
                </Group>
                {group.modifiers.length > 0 && (
                  <Table.ScrollContainer minWidth={300}>
                    <Table striped>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Opción</Table.Th>
                          <Table.Th style={{ textAlign: "right" }}>Precio</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {group.modifiers.map((mod) => (
                          <Table.Tr key={mod.id}>
                            <Table.Td>{mod.nombre}</Table.Td>
                            <Table.Td className="num-tabular">
                              {mod.precio_delta > 0
                                ? `+$${Number(mod.precio_delta).toLocaleString()}`
                                : mod.precio_delta < 0
                                  ? `-$${Math.abs(Number(mod.precio_delta)).toLocaleString()}`
                                  : "$0"}
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Table.ScrollContainer>
                )}
              </Card>
            ))}
          </Stack>
        )}
      </SectionCard>

      <ModifierGroupForm opened={formOpened} onClose={handleClose} group={editing} />
    </Stack>
  );
}
