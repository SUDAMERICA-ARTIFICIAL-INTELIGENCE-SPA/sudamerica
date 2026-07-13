"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useActividad } from "@/hooks/useLentes";
import { Badge, Group, Skeleton, Stack, Text, ThemeIcon, Timeline } from "@mantine/core";
import { IconMessageCircle, IconShoppingCart, IconUserPlus } from "@tabler/icons-react";

function clp(n: number) {
  return `$${Intl.NumberFormat("es-CL").format(Math.round(n || 0))}`;
}
function cuando(s: string) {
  const d = new Date(s);
  return d.toLocaleDateString("es-CL", { day: "2-digit", month: "short" }) + " " + d.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
}
type Meta = { color: string; icon: typeof IconShoppingCart; label: string };
const FALLBACK_META: Meta = { color: "teal", icon: IconShoppingCart, label: "Venta" };
const META: Record<string, Meta> = {
  VENTA: FALLBACK_META,
  LEAD: { color: "indigo", icon: IconUserPlus, label: "Nuevo lead" },
  CONVERSACION: { color: "grape", icon: IconMessageCircle, label: "Conversación" },
};

export default function Page() {
  const { data, isLoading } = useActividad(40);

  return (
    <Stack gap="lg">
      <PageHeader title="Actividad reciente" subtitle="Ventas, nuevos contactos y conversaciones del negocio" />
      <SectionCard>
        {isLoading ? (
          <Stack gap="md">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} height={40} radius="sm" />)}</Stack>
        ) : !data || data.length === 0 ? (
          <EmptyState title="Sin actividad" description="Aún no hay eventos recientes." />
        ) : (
          <Timeline active={data.length} bulletSize={28} lineWidth={2}>
            {data.map((a, i) => {
              const m = META[a.tipo] ?? FALLBACK_META;
              const Icon = m.icon;
              return (
                <Timeline.Item key={i} bullet={<ThemeIcon size={28} radius="xl" color={m.color} variant="light"><Icon size={16} /></ThemeIcon>} title={
                  <Group gap="xs">
                    <Text fw={500} size="sm">{a.titulo}</Text>
                    {a.monto != null && <Badge variant="light" color="teal" radius="sm">{clp(a.monto)}</Badge>}
                  </Group>
                }>
                  <Text size="xs" c="dimmed">{[m.label, a.subtitulo].filter(Boolean).join(" · ")}</Text>
                  <Text size="xs" c="dimmed" mt={2}>{cuando(a.fecha)}</Text>
                </Timeline.Item>
              );
            })}
          </Timeline>
        )}
      </SectionCard>
    </Stack>
  );
}
