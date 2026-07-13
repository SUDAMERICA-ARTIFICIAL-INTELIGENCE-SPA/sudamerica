"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useSmartAlerts } from "@/hooks/useSmartAlerts";
import { Badge, Checkbox, Group, Paper, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";
import { IconChecklist } from "@tabler/icons-react";

function fecha(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" });
}

type Meta = { color: string; label: string; prioridad: string };
const FALLBACK_META: Meta = { color: "gray", label: "Tarea pendiente", prioridad: "Normal" };
const META: Record<string, Meta> = {
  hot_lead: { color: "red", label: "Contactar cliente caliente", prioridad: "Alta" },
  stalled_deal: { color: "orange", label: "Reactivar trato estancado", prioridad: "Media" },
  churn_risk: { color: "grape", label: "Retener cliente en riesgo", prioridad: "Alta" },
  anomaly_detected: { color: "yellow", label: "Revisar anomalía", prioridad: "Media" },
  no_show_risk: { color: "cyan", label: "Confirmar cita (riesgo no-show)", prioridad: "Media" },
};

export default function Page() {
  const { data, isLoading } = useSmartAlerts({ page_size: 50 });
  const alerts = data?.data ?? [];
  // Pendientes (no leídas) primero
  const tareas = [...alerts].sort((a, b) => Number(a.leido) - Number(b.leido));
  const pendientes = alerts.filter((a) => !a.leido).length;
  const completadas = alerts.length - pendientes;

  return (
    <Stack gap="lg">
      <PageHeader title="Tareas del día" subtitle="Acciones sugeridas por el asistente para no perder oportunidades" />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Tareas pendientes" value={pendientes} isLoading={isLoading} color="orange" icon={<IconChecklist size={18} />} />
        <KpiCard title="Completadas" value={completadas} isLoading={isLoading} color="teal" />
      </SimpleGrid>

      <SectionCard title="Lista de tareas">
        {isLoading ? (
          <Stack gap="sm">{[0, 1, 2, 3].map((i) => <Skeleton key={i} height={56} radius="md" />)}</Stack>
        ) : tareas.length === 0 ? (
          <EmptyState icon={<IconChecklist size={40} />} title="Todo al día" description="No hay tareas pendientes por ahora." />
        ) : (
          <Stack gap="sm">
            {tareas.map((a) => {
              const m = META[a.tipo] ?? FALLBACK_META;
              return (
                <Paper key={a.id} p="md" radius="md" withBorder>
                  <Group justify="space-between" wrap="nowrap" align="flex-start">
                    <Group gap="sm" wrap="nowrap" align="flex-start">
                      <Checkbox checked={a.leido} readOnly color={m.color} mt={2} aria-label="Estado de la tarea" />
                      <Stack gap={2}>
                        {a.leido ? (
                          <Text fw={500} size="sm" td="line-through" c="dimmed">{m.label}</Text>
                        ) : (
                          <Text fw={500} size="sm">{m.label}</Text>
                        )}
                        <Text size="sm" c="dimmed">{a.mensaje}</Text>
                      </Stack>
                    </Group>
                    <Stack gap={4} align="flex-end">
                      <Badge size="sm" color={m.color} variant="light" radius="sm">{m.prioridad}</Badge>
                      <Text size="xs" c="dimmed">{fecha(a.created_at)}</Text>
                    </Stack>
                  </Group>
                </Paper>
              );
            })}
          </Stack>
        )}
      </SectionCard>
    </Stack>
  );
}
