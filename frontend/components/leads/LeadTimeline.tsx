"use client";

import { useLeadInteractions } from "@/hooks/useLeadInteractions";
import { useLeadStageHistory } from "@/hooks/useLeadStageHistory";
import { InteractionTipo } from "@/lib/enums";
import type { LeadInteraction, LeadStageHistory } from "@/lib/types";
import { Badge, Group, Skeleton, Stack, Text, ThemeIcon, Timeline } from "@mantine/core";
import {
  IconArrowRight,
  IconBrandWhatsapp,
  IconFileText,
  IconMail,
  IconMessageCircle,
  IconPhone,
  IconUsers,
} from "@tabler/icons-react";
import type { ReactNode } from "react";

// ─── Icon map ─────────────────────────────────────────────────────────────────

const INTERACTION_ICON: Record<string, ReactNode> = {
  [InteractionTipo.LLAMADA]: <IconPhone size={14} />,
  [InteractionTipo.NOTA]: <IconFileText size={14} />,
  [InteractionTipo.EMAIL]: <IconMail size={14} />,
  [InteractionTipo.WHATSAPP]: <IconBrandWhatsapp size={14} />,
  [InteractionTipo.REUNION]: <IconUsers size={14} />,
};

const INTERACTION_COLOR: Record<string, string> = {
  [InteractionTipo.LLAMADA]: "teal",
  [InteractionTipo.NOTA]: "gray",
  [InteractionTipo.EMAIL]: "blue",
  [InteractionTipo.WHATSAPP]: "green",
  [InteractionTipo.REUNION]: "violet",
};

const ESTADO_LABEL: Record<string, string> = {
  NUEVO: "Nuevo",
  CONTACTADO: "Contactado",
  EN_PROCESO: "En Proceso",
  CONVERTIDO: "Convertido",
  DESCARTADO: "Descartado",
};

const ESTADO_COLOR: Record<string, string> = {
  NUEVO: "blue",
  CONTACTADO: "cyan",
  EN_PROCESO: "yellow",
  CONVERTIDO: "green",
  DESCARTADO: "gray",
};

// ─── Unified event type ───────────────────────────────────────────────────────

type TimelineEvent =
  | { kind: "interaction"; data: LeadInteraction }
  | { kind: "stage"; data: LeadStageHistory };

function sortedTimeline(
  interactions: LeadInteraction[],
  history: LeadStageHistory[],
): TimelineEvent[] {
  const events: TimelineEvent[] = [
    ...interactions.map((d): TimelineEvent => ({ kind: "interaction", data: d })),
    ...history.map((d): TimelineEvent => ({ kind: "stage", data: d })),
  ];
  return events.sort(
    (a, b) => new Date(b.data.created_at).getTime() - new Date(a.data.created_at).getTime(),
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "ahora";
  if (mins < 60) return `hace ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface LeadTimelineProps {
  leadId: string;
}

export function LeadTimeline({ leadId }: LeadTimelineProps) {
  const { data: interactionsData, isLoading: iLoading } = useLeadInteractions(leadId);
  const { data: historyData, isLoading: hLoading } = useLeadStageHistory(leadId);

  if (iLoading || hLoading) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} height={52} radius="sm" />
        ))}
      </Stack>
    );
  }

  const events = sortedTimeline(interactionsData?.data ?? [], historyData?.data ?? []);

  if (events.length === 0) {
    return (
      <Stack align="center" gap="xs" py="xl">
        <ThemeIcon size={48} radius="xl" color="gray" variant="light" aria-hidden="true">
          <IconMessageCircle size={24} />
        </ThemeIcon>
        <Text size="sm" c="dimmed" ta="center">
          Sin actividad registrada todavía.
        </Text>
      </Stack>
    );
  }

  return (
    <Timeline bulletSize={28} lineWidth={2} aria-label="Timeline de actividad del lead">
      {events.map((ev) => {
        if (ev.kind === "interaction") {
          const icon = INTERACTION_ICON[ev.data.tipo] ?? <IconMessageCircle size={14} />;
          const color = INTERACTION_COLOR[ev.data.tipo] ?? "gray";
          return (
            <Timeline.Item
              key={ev.data.id}
              bullet={
                <ThemeIcon size={24} radius="xl" color={color} variant="filled" aria-hidden="true">
                  {icon}
                </ThemeIcon>
              }
              title={
                <Group gap={6}>
                  <Badge size="xs" color={color} variant="light">
                    {ev.data.tipo}
                  </Badge>
                  <Text fz={11} c="dimmed">
                    {formatRelative(ev.data.created_at)}
                  </Text>
                </Group>
              }
            >
              <Text size="sm" c="dimmed" mt={2}>
                {ev.data.descripcion}
              </Text>
            </Timeline.Item>
          );
        }

        // Stage transition
        const prev = ev.data.estado_anterior;
        const next = ev.data.estado_nuevo;
        return (
          <Timeline.Item
            key={ev.data.id}
            bullet={
              <ThemeIcon size={24} radius="xl" color="indigo" variant="light" aria-hidden="true">
                <IconArrowRight size={14} />
              </ThemeIcon>
            }
            title={
              <Group gap={4}>
                <Text fz={12} fw={500}>
                  Estado cambiado
                </Text>
                <Text fz={11} c="dimmed">
                  {formatRelative(ev.data.created_at)}
                </Text>
              </Group>
            }
          >
            <Group gap={6} mt={2}>
              {prev && (
                <Badge size="xs" color={ESTADO_COLOR[prev] ?? "gray"} variant="light">
                  {ESTADO_LABEL[prev] ?? prev}
                </Badge>
              )}
              <IconArrowRight size={12} color="var(--mantine-color-dimmed)" />
              <Badge size="xs" color={ESTADO_COLOR[next] ?? "blue"} variant="filled">
                {ESTADO_LABEL[next] ?? next}
              </Badge>
            </Group>
          </Timeline.Item>
        );
      })}
    </Timeline>
  );
}
