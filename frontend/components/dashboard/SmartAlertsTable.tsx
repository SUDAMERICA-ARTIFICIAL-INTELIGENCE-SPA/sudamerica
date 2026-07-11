"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useMarkAlertRead, useSmartAlerts } from "@/hooks/useSmartAlerts";
import { SmartAlertType } from "@/lib/enums";
import type { SmartAlert } from "@/lib/types";
import { ActionIcon, Badge, Group, Skeleton, Stack, Text, Tooltip } from "@mantine/core";
import { IconCheck } from "@tabler/icons-react";

const ALERT_CONFIG: Record<SmartAlertType, { emoji: string; color: string; label: string }> = {
  [SmartAlertType.HOT_LEAD]: { emoji: "🔥", color: "red", label: "Lead Caliente" },
  [SmartAlertType.STALLED_DEAL]: { emoji: "⏳", color: "yellow", label: "Sin actividad" },
  [SmartAlertType.CHURN_RISK]: { emoji: "📉", color: "red", label: "Riesgo Churn" },
  [SmartAlertType.ANOMALY_DETECTED]: { emoji: "⚠️", color: "orange", label: "Anomalía" },
  [SmartAlertType.NO_SHOW_RISK]: { emoji: "🚫", color: "gray", label: "No-Show" },
};

function AlertRow({ alert }: { alert: SmartAlert }) {
  const { mutate: markRead } = useMarkAlertRead();
  const config = ALERT_CONFIG[alert.tipo] ?? { emoji: "📌", color: "blue", label: alert.tipo };

  return (
    <Group
      justify="space-between"
      py="xs"
      px="sm"
      style={{
        borderRadius: "8px",
        backgroundColor: alert.leido ? "transparent" : `var(--mantine-color-${config.color}-light)`,
        borderLeft: alert.leido ? "none" : `3px solid var(--mantine-color-${config.color}-5)`,
      }}
    >
      <Group gap="sm">
        <Text size="lg" role="img" aria-hidden="true">
          {config.emoji}
        </Text>
        <Stack gap={2}>
          <Badge color={config.color} variant="light" size="xs">
            {config.label}
          </Badge>
          <Text size="xs" c="dimmed" lineClamp={2}>
            {alert.mensaje}
          </Text>
        </Stack>
      </Group>
      {!alert.leido && (
        <Tooltip label="Marcar como leída">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            aria-label="Marcar alerta como leída"
            onClick={() => markRead(alert.id)}
          >
            <IconCheck size={14} />
          </ActionIcon>
        </Tooltip>
      )}
    </Group>
  );
}

export function SmartAlertsTable() {
  const { data, isLoading } = useSmartAlerts({ leido: false, page_size: 8 });

  return (
    <SectionCard
      title="Alertas Activas"
      fullHeight
      action={
        data?.meta && (
          <Badge
            variant="filled"
            size="xs"
            color="red"
            aria-label={`${data.meta.total} alertas sin leer`}
          >
            {data.meta.total}
          </Badge>
        )
      }
    >
      {isLoading ? (
        <Stack gap="xs">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={52} radius="sm" />
          ))}
        </Stack>
      ) : data?.data.length ? (
        <Stack gap={4}>
          {data.data.map((alert) => (
            <AlertRow key={alert.id} alert={alert} />
          ))}
        </Stack>
      ) : (
        <EmptyState icon="✅" title="Sin alertas pendientes" description="Todo en orden." />
      )}
    </SectionCard>
  );
}
