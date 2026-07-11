"use client";

import {
  useCreateSubentidad,
  useDeleteSubentidad,
  useSubentidades,
  useUpdateSubentidad,
} from "@/hooks/useSubentidades";
import type { ClienteSubentidad } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useState } from "react";

interface SubentidadRowProps {
  sub: ClienteSubentidad;
  onRename: (nombre: string) => void;
  onDelete: () => void;
  isDeleting: boolean;
}

function SubentidadRow({ sub, onRename, onDelete, isDeleting }: SubentidadRowProps) {
  return (
    <Group gap="sm" wrap="nowrap">
      <TextInput
        defaultValue={sub.nombre}
        aria-label={`Nombre de ${sub.nombre}`}
        onBlur={(e) => {
          const nombre = e.currentTarget.value.trim();
          if (nombre && nombre !== sub.nombre) onRename(nombre);
        }}
        style={{ flex: 1 }}
      />
      <Badge variant="light" color="indigo">
        {sub.tipo}
      </Badge>
      <Tooltip label="Eliminar" withArrow>
        <ActionIcon
          variant="subtle"
          color="red"
          onClick={onDelete}
          loading={isDeleting}
          aria-label={`Eliminar ${sub.nombre}`}
        >
          <IconTrash size={16} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );
}

interface SubentidadesPanelProps {
  leadId: string;
  /** Label singular de la sub-entidad del rubro (Mascota/Vehículo/Paciente…). */
  label: string;
}

/** CRUD de sub-entidades del cliente; montar solo con módulo sub_entidad ON. */
export function SubentidadesPanel({ leadId, label }: SubentidadesPanelProps) {
  const { data: subentidades, isLoading } = useSubentidades(leadId);
  const createSub = useCreateSubentidad(leadId);
  const updateSub = useUpdateSubentidad(leadId);
  const deleteSub = useDeleteSubentidad(leadId);
  const [nuevoNombre, setNuevoNombre] = useState("");

  const handleCreate = () => {
    const nombre = nuevoNombre.trim();
    if (!nombre) return;
    createSub.mutate(
      { lead_id: leadId, tipo: label.toLowerCase(), nombre },
      { onSuccess: () => setNuevoNombre("") },
    );
  };

  if (isLoading) {
    return <Skeleton height={120} radius="sm" />;
  }

  return (
    <Stack gap="md">
      <Group gap="sm" align="flex-end" wrap="nowrap">
        <TextInput
          label="Nombre"
          placeholder={`Nombre de ${label.toLowerCase()}`}
          value={nuevoNombre}
          onChange={(e) => setNuevoNombre(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Button
          leftSection={<IconPlus size={16} />}
          onClick={handleCreate}
          loading={createSub.isPending}
          disabled={!nuevoNombre.trim()}
          aria-label={`Agregar ${label.toLowerCase()}`}
        >
          Agregar
        </Button>
      </Group>

      {(subentidades ?? []).length === 0 ? (
        <Text c="dimmed" ta="center" py="md">
          Sin registros todavía.
        </Text>
      ) : (
        <Stack gap="xs">
          {(subentidades ?? []).map((sub) => (
            <SubentidadRow
              key={sub.id}
              sub={sub}
              onRename={(nombre) => updateSub.mutate({ id: sub.id, dto: { nombre } })}
              onDelete={() => deleteSub.mutate(sub.id)}
              isDeleting={deleteSub.isPending && deleteSub.variables === sub.id}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}
