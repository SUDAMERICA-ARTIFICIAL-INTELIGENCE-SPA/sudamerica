"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import {
  type Reservacion,
  useCancelReservacion,
  useReservaciones,
  useUpdateReservacion,
} from "@/hooks/useReservaciones";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import { SEMANTIC } from "@/lib/theme-tokens";
import {
  ActionIcon,
  Badge,
  Group,
  Menu,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import { IconCalendar, IconCheck, IconDots, IconUsers, IconX } from "@tabler/icons-react";
import { useState } from "react";

const ESTADO_COLORS: Record<string, string> = {
  PENDIENTE: SEMANTIC.warning,
  CONFIRMADA: SEMANTIC.success,
  CANCELADA: SEMANTIC.danger,
  COMPLETADA: "blue",
  NO_SHOW: "gray",
};

const ESTADO_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "PENDIENTE", label: "Pendiente" },
  { value: "CONFIRMADA", label: "Confirmada" },
  { value: "CANCELADA", label: "Cancelada" },
  { value: "COMPLETADA", label: "Completada" },
  { value: "NO_SHOW", label: "No Show" },
];

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-CL", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatTime(time: string): string {
  return time.slice(0, 5);
}

function ReservacionRow({ r }: { r: Reservacion }) {
  const cancel = useCancelReservacion();
  const update = useUpdateReservacion();

  return (
    <Table.Tr>
      <Table.Td>
        <Text fw={600} size="sm">
          {r.nombre_cliente}
        </Text>
        {r.rut && (
          <Text size="xs" c="dimmed">
            {r.rut}
          </Text>
        )}
      </Table.Td>
      <Table.Td>
        <Text size="sm">{formatDate(r.fecha_reserva)}</Text>
      </Table.Td>
      <Table.Td>
        <Text size="sm">
          {formatTime(r.hora_inicio)} - {formatTime(r.hora_fin)}
        </Text>
      </Table.Td>
      <Table.Td className="num-tabular">
        <Group gap={4} justify="flex-end" wrap="nowrap">
          <IconUsers size={14} />
          <Text size="sm">{r.cantidad_personas}</Text>
        </Group>
      </Table.Td>
      <Table.Td>
        <Badge color={ESTADO_COLORS[r.estado] ?? "gray"} variant="light" size="sm">
          {r.estado}
        </Badge>
      </Table.Td>
      <Table.Td>
        <Text size="xs" c="dimmed">
          {r.email}
        </Text>
      </Table.Td>
      <Table.Td>
        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <ActionIcon variant="subtle" size="sm" aria-label="Acciones">
              <IconDots size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            {r.estado === "PENDIENTE" && (
              <Menu.Item
                leftSection={<IconCheck size={14} />}
                onClick={() => update.mutate({ id: r.id, estado: "CONFIRMADA" })}
              >
                Confirmar
              </Menu.Item>
            )}
            {r.estado !== "CANCELADA" && r.estado !== "COMPLETADA" && (
              <Menu.Item
                color="red"
                leftSection={<IconX size={14} />}
                onClick={() => cancel.mutate(r.id)}
              >
                Cancelar
              </Menu.Item>
            )}
            {r.estado === "CONFIRMADA" && (
              <Menu.Item
                leftSection={<IconCheck size={14} />}
                onClick={() => update.mutate({ id: r.id, estado: "COMPLETADA" })}
              >
                Marcar completada
              </Menu.Item>
            )}
          </Menu.Dropdown>
        </Menu>
      </Table.Td>
    </Table.Tr>
  );
}

export default function ReservacionesPage() {
  const rubro = useRubroLabels();
  const [fechaFilter, setFechaFilter] = useState<Date | null>(null);
  const [estadoFilter, setEstadoFilter] = useState("");

  const titulo = rubro.key === RUBRO_DEFAULT ? "Reservaciones" : plural(rubro.labels.agenda);

  const fecha = fechaFilter ? fechaFilter.toISOString().split("T")[0] : undefined;
  const { data, isLoading } = useReservaciones(fecha, estadoFilter || undefined);

  const reservaciones = data?.data ?? [];
  const total = data?.meta?.total ?? 0;

  return (
    <Stack gap="lg">
      <PageHeader
        title={titulo}
        actions={
          <Badge variant="light" color="indigo" size="lg">
            {total}
          </Badge>
        }
      />

      <Group gap="sm">
        <DatePickerInput
          placeholder="Filtrar por fecha"
          value={fechaFilter}
          onChange={setFechaFilter}
          clearable
          style={{ width: 200 }}
          aria-label="Filtrar por fecha"
        />
        <Select
          placeholder="Estado"
          data={ESTADO_OPTIONS}
          value={estadoFilter}
          onChange={(v) => setEstadoFilter(v ?? "")}
          clearable
          style={{ width: 160 }}
          aria-label="Filtrar por estado"
        />
      </Group>

      <SectionCard noBodyPadding>
        {isLoading ? (
          <Stack gap="sm" p="md">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={`skel-${i}`} height={40} radius="sm" />
            ))}
          </Stack>
        ) : reservaciones.length === 0 ? (
          <EmptyState
            icon={<IconCalendar size={40} color="var(--mantine-color-gray-4)" />}
            title={`No hay reservaciones${fecha ? " para esta fecha" : ""}`}
          />
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Cliente</Table.Th>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Horario</Table.Th>
                <Table.Th style={{ textAlign: "right" }}>Personas</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th w={50} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {reservaciones.map((r) => (
                <ReservacionRow key={r.id} r={r} />
              ))}
            </Table.Tbody>
          </Table>
        )}
      </SectionCard>
    </Stack>
  );
}
