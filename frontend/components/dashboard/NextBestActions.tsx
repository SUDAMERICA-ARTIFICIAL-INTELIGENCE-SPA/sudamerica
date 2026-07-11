"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { useRevisionHumana } from "@/hooks/useRevisionHumana";
import { useSmartAlerts } from "@/hooks/useSmartAlerts";
import { SmartAlertType } from "@/lib/enums";
import type { SmartAlert } from "@/lib/types";
import { Badge, Button, Group, Skeleton, Stack, Text } from "@mantine/core";
import { IconArrowRight, IconCheck, IconEye } from "@tabler/icons-react";
import { useRouter } from "next/navigation";

const ALERT_CONFIG: Record<
  SmartAlertType,
  { emoji: string; color: string; cta: string; href: string }
> = {
  [SmartAlertType.HOT_LEAD]: {
    emoji: "🔥",
    color: "red",
    cta: "Ver en Pipeline",
    href: "/pipeline",
  },
  [SmartAlertType.STALLED_DEAL]: {
    emoji: "⏳",
    color: "yellow",
    cta: "Ver Leads",
    href: "/leads",
  },
  [SmartAlertType.CHURN_RISK]: {
    emoji: "📉",
    color: "orange",
    cta: "Ver Lead",
    href: "/leads",
  },
  [SmartAlertType.ANOMALY_DETECTED]: {
    emoji: "⚠️",
    color: "orange",
    cta: "Ver Dashboard",
    href: "/dashboard",
  },
  [SmartAlertType.NO_SHOW_RISK]: {
    emoji: "🚫",
    color: "gray",
    cta: "Ver Calendario",
    href: "/calendario",
  },
};

function ActionCard({ alert }: { alert: SmartAlert }) {
  const router = useRouter();
  const config = ALERT_CONFIG[alert.tipo] ?? {
    emoji: "📌",
    color: "blue",
    cta: "Ver",
    href: "/dashboard",
  };

  return (
    <Group
      justify="space-between"
      align="center"
      p="sm"
      wrap="wrap"
      gap="xs"
      style={{
        borderRadius: 8,
        border: `1px solid var(--mantine-color-${config.color}-light)`,
        backgroundColor: `var(--mantine-color-${config.color}-light)`,
      }}
    >
      <Group gap="sm" style={{ flex: 1, minWidth: 0 }} wrap="nowrap">
        <Text size="xl" role="img" aria-hidden="true" style={{ flexShrink: 0 }}>
          {config.emoji}
        </Text>
        <Text size="sm" lineClamp={2} style={{ flex: 1, minWidth: 0 }}>
          {alert.mensaje}
        </Text>
      </Group>
      <Button
        size="xs"
        variant="light"
        color={config.color}
        radius="md"
        rightSection={<IconArrowRight size={12} />}
        onClick={() => router.push(config.href)}
        aria-label={`${config.cta}: ${alert.mensaje}`}
        style={{ flexShrink: 0 }}
      >
        {config.cta}
      </Button>
    </Group>
  );
}

export function NextBestActions() {
  const { data: alerts, isLoading: alertsLoading } = useSmartAlerts({
    leido: false,
    page_size: 3,
  });
  const { data: reviews, isLoading: reviewsLoading } = useRevisionHumana({
    pendiente: true,
    page_size: 3,
  });
  const router = useRouter();

  const isLoading = alertsLoading || reviewsLoading;

  if (isLoading) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} height={52} radius="sm" />
        ))}
      </Stack>
    );
  }

  const alertItems = alerts?.data ?? [];
  const reviewCount = reviews?.meta.total ?? 0;
  const hasActions = alertItems.length > 0 || reviewCount > 0;

  if (!hasActions) {
    return (
      <EmptyState
        icon="✅"
        title="¡Todo en orden!"
        description="No hay acciones urgentes pendientes."
      />
    );
  }

  return (
    <Stack gap="sm">
      {reviewCount > 0 && (
        <Group
          justify="space-between"
          align="center"
          p="sm"
          wrap="wrap"
          gap="xs"
          style={{
            borderRadius: 8,
            border: "1px solid var(--mantine-color-violet-light)",
            backgroundColor: "var(--mantine-color-violet-light)",
          }}
        >
          <Group gap="sm">
            <Text size="xl" role="img" aria-hidden="true">
              🤖
            </Text>
            <Stack gap={0}>
              <Text size="sm" fw={600}>
                Revisión humana pendiente
              </Text>
              <Text fz={11} c="dimmed">
                <Badge size="xs" color="violet" variant="filled" mr={4}>
                  {reviewCount}
                </Badge>
                conversaciones IA requieren tu aprobación
              </Text>
            </Stack>
          </Group>
          <Button
            size="xs"
            variant="light"
            color="violet"
            radius="md"
            rightSection={<IconEye size={12} />}
            onClick={() => router.push("/ia")}
            aria-label="Ver revisiones humanas pendientes"
          >
            Revisar
          </Button>
        </Group>
      )}

      {alertItems.map((alert) => (
        <ActionCard key={alert.id} alert={alert} />
      ))}

      {alertItems.length > 0 && (
        <Group justify="flex-end">
          <Button
            size="xs"
            variant="subtle"
            color="gray"
            rightSection={<IconCheck size={12} />}
            onClick={() => router.push("/ia")}
            aria-label="Ver todas las alertas"
          >
            Ver todas las alertas
          </Button>
        </Group>
      )}
    </Stack>
  );
}
