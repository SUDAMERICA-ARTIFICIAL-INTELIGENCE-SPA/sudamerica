"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useSmartAlerts } from "@/hooks/useSmartAlerts";
import { Badge, Group, Paper, SimpleGrid, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconAlertTriangle, IconBell, IconCalendarX, IconClock, IconFlame, IconUserX } from "@tabler/icons-react";

function fecha(s: string | null) {
  if (!s) return "—";
  const d = new Date(s);
  return (
    d.toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "2-digit" }) +
    " " +
    d.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })
  );
}

type Meta = { color: string; icon: typeof IconBell; label: string };
const FALLBACK_META: Meta = { color: "gray", icon: IconBell, label: "Notificación" };
const META: Record<string, Meta> = {
  hot_lead: { color: "red", icon: IconFlame, label: "Cliente caliente" },
  stalled_deal: { color: "orange", icon: IconClock, label: "Trato estancado" },
  churn_risk: { color: "grape", icon: IconUserX, label: "Riesgo de fuga" },
  anomaly_detected: { color: "yellow", icon: IconAlertTriangle, label: "Anomalía detectada" },
  no_show_risk: { color: "cyan", icon: IconCalendarX, label: "Riesgo de no-show" },
};

export default function Page() {
  const { data, isLoading } = useSmartAlerts({ page_size: 50 });
  const alerts = data?.data ?? [];
  const total = alerts.length;
  const noLeidas = alerts.filter((a) => !a.leido).length;

  return (
    <Stack gap="lg">
      <PageHeader
        title="Notificaciones"
        subtitle="Alertas inteligentes del negocio: clientes en riesgo, oportunidades y anomalías"
      />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <KpiCard title="Total notificaciones" value={total} isLoading={isLoading} icon={<IconBell size={18} />} />
        <KpiCard title="Sin leer" value={noLeidas} isLoading={isLoading} color="red" />
      </SimpleGrid>

      <SectionCard title="Bandeja de notificaciones">
        {isLoading ? (
          <Stack gap="sm">{[0, 1, 2, 3].map((i) => <Skeleton key={i} height={64} radius="md" />)}</Stack>
        ) : total === 0 ? (
          <EmptyState icon={<IconBell size={40} />} title="Sin notificaciones" description="No hay alertas pendientes por ahora." />
        ) : (
          <Stack gap="sm">
            {alerts.map((a) => {
              const m = META[a.tipo] ?? FALLBACK_META;
              const Icon = m.icon;
              return (
                <Paper
                  key={a.id}
                  p="md"
                  radius="md"
                  withBorder
                  style={{ borderLeft: `3px solid var(--mantine-color-${a.leido ? "gray" : m.color}-5)` }}
                >
                  <Group justify="space-between" wrap="nowrap" align="flex-start">
                    <Group gap="sm" wrap="nowrap" align="flex-start">
                      <ThemeIcon size={36} radius="xl" color={m.color} variant="light">
                        <Icon size={18} />
                      </ThemeIcon>
                      <Stack gap={2}>
                        <Group gap="xs">
                          <Text fw={500} size="sm">{m.label}</Text>
                          {!a.leido && (
                            <Badge size="xs" color={m.color} variant="filled" radius="sm">No leído</Badge>
                          )}
                        </Group>
                        <Text size="sm" c="dimmed">{a.mensaje}</Text>
                      </Stack>
                    </Group>
                    <Text size="xs" c="dimmed" style={{ whiteSpace: "nowrap" }}>{fecha(a.created_at)}</Text>
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
