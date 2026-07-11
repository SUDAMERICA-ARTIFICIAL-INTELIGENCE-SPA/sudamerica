"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { useCalendarEvents, useCreateCalendarEvent } from "@/hooks/useCalendarEvents";
import { CalendarEventTipo } from "@/lib/enums";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import type { CalendarEvent } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  Select,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import {
  IconCalendarEvent,
  IconChevronLeft,
  IconChevronRight,
  IconPlus,
} from "@tabler/icons-react";
import { useState } from "react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const TIPO_COLOR: Record<CalendarEventTipo, string> = {
  [CalendarEventTipo.LLAMADA]: "teal",
  [CalendarEventTipo.REUNION]: "indigo",
  [CalendarEventTipo.SEGUIMIENTO]: "orange",
  [CalendarEventTipo.DEMO]: "violet",
};

const TIPO_OPTIONS = Object.values(CalendarEventTipo).map((t) => ({
  value: t,
  label: t.charAt(0) + t.slice(1).toLowerCase(),
}));

const WEEK_DAYS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

function isoDate(year: number, month: number, day: number): string {
  const mm = String(month + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

// ─── Create event modal ───────────────────────────────────────────────────────

interface CreateEventModalProps {
  opened: boolean;
  onClose: () => void;
  defaultDate?: string;
}

function CreateEventModal({ opened, onClose, defaultDate }: CreateEventModalProps) {
  const { mutate: create, isPending } = useCreateCalendarEvent();

  const form = useForm({
    initialValues: {
      titulo: "",
      tipo: CalendarEventTipo.REUNION as CalendarEventTipo,
      fecha_inicio: defaultDate ?? new Date().toISOString().slice(0, 10),
      descripcion: "",
    },
    validate: {
      titulo: (v) => (v.trim().length < 2 ? "Título requerido" : null),
    },
  });

  function handleSubmit(values: typeof form.values) {
    create(
      {
        ...values,
        fecha_inicio: `${values.fecha_inicio}T09:00:00`,
        ...(values.descripcion ? { descripcion: values.descripcion } : {}),
      },
      {
        onSuccess: () => {
          form.reset();
          onClose();
        },
      },
    );
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Nuevo evento" radius="md" size="sm">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <TextInput
            label="Título"
            placeholder="Reunión con cliente…"
            radius="md"
            aria-label="Título del evento"
            {...form.getInputProps("titulo")}
          />
          <Select
            label="Tipo"
            data={TIPO_OPTIONS}
            radius="md"
            allowDeselect={false}
            aria-label="Tipo de evento"
            {...form.getInputProps("tipo")}
          />
          <TextInput
            label="Fecha"
            type="date"
            radius="md"
            aria-label="Fecha del evento"
            {...form.getInputProps("fecha_inicio")}
          />
          <Textarea
            label="Descripción (opcional)"
            placeholder="Notas adicionales…"
            radius="md"
            minRows={2}
            aria-label="Descripción del evento"
            {...form.getInputProps("descripcion")}
          />
          <Group justify="flex-end" mt="xs">
            <Button variant="subtle" color="gray" radius="md" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" color="indigo" radius="md" loading={isPending}>
              Crear evento
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

// ─── Day cell ─────────────────────────────────────────────────────────────────

function DayCell({
  day,
  year,
  month,
  events,
  isToday,
  onAdd,
}: {
  day: number;
  year: number;
  month: number;
  events: CalendarEvent[];
  isToday: boolean;
  onAdd: (date: string) => void;
}) {
  const dateStr = isoDate(year, month, day);

  return (
    <Paper
      p={4}
      radius="sm"
      style={{
        minHeight: 80,
        border: isToday
          ? "2px solid var(--mantine-color-indigo-5)"
          : "1px solid var(--mantine-color-default-border)",
        backgroundColor: isToday
          ? "var(--mantine-color-indigo-light)"
          : "var(--mantine-color-body)",
        cursor: "pointer",
        position: "relative",
        transition: "background-color 200ms ease-out",
      }}
      onClick={() => onAdd(dateStr)}
      onMouseEnter={(e) => {
        if (isToday) return;
        (e.currentTarget as HTMLDivElement).style.backgroundColor =
          "var(--mantine-color-default-hover)";
      }}
      onMouseLeave={(e) => {
        if (isToday) return;
        (e.currentTarget as HTMLDivElement).style.backgroundColor = "var(--mantine-color-body)";
      }}
      aria-label={`Día ${day}${events.length > 0 ? `, ${events.length} eventos` : ""}`}
    >
      <Text fz={12} fw={isToday ? 700 : 400} {...(isToday ? { c: "indigo" } : {})} mb={2}>
        {day}
      </Text>
      <Stack gap={2}>
        {events.slice(0, 2).map((ev) => (
          <Badge
            key={ev.id}
            size="xs"
            color={TIPO_COLOR[ev.tipo] ?? "gray"}
            variant="light"
            radius="sm"
            tt="none"
            fw={500}
            style={{
              maxWidth: "100%",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {ev.titulo}
          </Badge>
        ))}
        {events.length > 2 && (
          <Text fz={10} c="dimmed">
            +{events.length - 2} más
          </Text>
        )}
      </Stack>
    </Paper>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CalendarView() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [modalOpen, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [selectedDate, setSelectedDate] = useState<string | undefined>();

  const mm = String(month + 1).padStart(2, "0");
  const { data, isLoading } = useCalendarEvents({
    fecha_desde: `${year}-${mm}-01`,
    fecha_hasta: isoDate(year, month, getDaysInMonth(year, month)),
    page_size: 100,
  });

  function prevMonth() {
    if (month === 0) {
      setYear((y) => y - 1);
      setMonth(11);
    } else setMonth((m) => m - 1);
  }

  function nextMonth() {
    if (month === 11) {
      setYear((y) => y + 1);
      setMonth(0);
    } else setMonth((m) => m + 1);
  }

  function handleDayClick(date: string) {
    setSelectedDate(date);
    openModal();
  }

  const events = data?.data ?? [];
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfWeek(year, month);

  // Group events by day
  const byDay: Record<number, CalendarEvent[]> = {};
  for (const ev of events) {
    const d = new Date(ev.fecha_inicio).getDate();
    const existing = byDay[d];
    if (existing) {
      existing.push(ev);
    } else {
      byDay[d] = [ev];
    }
  }

  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between" align="center">
        <Group gap="sm">
          <ActionIcon variant="subtle" radius="md" onClick={prevMonth} aria-label="Mes anterior">
            <IconChevronLeft size={18} />
          </ActionIcon>
          <Text fw={600} fz={16} style={{ minWidth: 160, textAlign: "center" }}>
            {MONTH_NAMES[month]} {year}
          </Text>
          <ActionIcon variant="subtle" radius="md" onClick={nextMonth} aria-label="Mes siguiente">
            <IconChevronRight size={18} />
          </ActionIcon>
        </Group>
        <Button
          size="sm"
          color="indigo"
          radius="md"
          leftSection={<IconPlus size={16} />}
          onClick={() => {
            setSelectedDate(undefined);
            openModal();
          }}
          aria-label="Crear nuevo evento"
        >
          Nuevo evento
        </Button>
      </Group>

      {/* Week day headers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 4,
        }}
        aria-hidden="true"
      >
        {WEEK_DAYS.map((d) => (
          <Text key={d} style={TYPOGRAPHY.sectionLabel} c="dimmed" ta="center">
            {d}
          </Text>
        ))}
      </div>

      {/* Calendar grid */}
      {isLoading ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, 1fr)",
            gap: 4,
          }}
        >
          {Array.from({ length: 35 }).map((_, i) => (
            <Skeleton key={i} height={80} radius="sm" />
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, 1fr)",
            gap: 4,
          }}
          aria-label={`Calendario ${MONTH_NAMES[month]} ${year}`}
        >
          {/* Empty cells before first day */}
          {Array.from({ length: firstDay }).map((_, i) => (
            <div key={`empty-${i}`} style={{ minHeight: 80 }} />
          ))}
          {/* Day cells */}
          {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
            const isToday =
              day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            return (
              <DayCell
                key={day}
                day={day}
                year={year}
                month={month}
                events={byDay[day] ?? []}
                isToday={isToday}
                onAdd={handleDayClick}
              />
            );
          })}
        </div>
      )}

      {/* No events state */}
      {!isLoading && events.length === 0 && (
        <EmptyState
          icon={<IconCalendarEvent size={40} color="var(--mantine-color-gray-4)" />}
          title="Sin eventos este mes. Haz clic en un día para agregar uno."
        />
      )}

      <CreateEventModal
        opened={modalOpen}
        onClose={closeModal}
        {...(selectedDate !== undefined ? { defaultDate: selectedDate } : {})}
      />
    </Stack>
  );
}
