"use client";

import { useMarkAlertRead, useSmartAlerts } from "@/hooks/useSmartAlerts";
import { SmartAlertType } from "@/lib/enums";
import type { SmartAlert } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Drawer,
  Group,
  Skeleton,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconBellOff, IconCheck } from "@tabler/icons-react";

const ALERT_CONFIG: Record<SmartAlertType, { emoji: string; color: string; label: string }> = {
  [SmartAlertType.HOT_LEAD]: { emoji: "🔥", color: "red", label: "Lead Caliente" },
  [SmartAlertType.STALLED_DEAL]: { emoji: "⏳", color: "yellow", label: "Sin actividad" },
  [SmartAlertType.CHURN_RISK]: { emoji: "📉", color: "orange", label: "Riesgo Churn" },
  [SmartAlertType.ANOMALY_DETECTED]: { emoji: "⚠️", color: "orange", label: "Anomalía" },
  [SmartAlertType.NO_SHOW_RISK]: { emoji: "🚫", color: "gray", label: "No-Show" },
};

function AlertItem({ alert }: { alert: SmartAlert }) {
  const { mutate: markRead, isPending } = useMarkAlertRead();
  const config = ALERT_CONFIG[alert.tipo] ?? { emoji: "📌", color: "blue", label: alert.tipo };

  return (
    <Group
      justify="space-between"
      py="xs"
      px="sm"
      style={{
        borderRadius: 8,
        backgroundColor: alert.leido ? "transparent" : `var(--mantine-color-${config.color}-0)`,
        borderLeft: alert.leido ? "none" : `3px solid var(--mantine-color-${config.color}-5)`,
        transition: "background-color 200ms",
      }}
    >
      <Group gap="sm" style={{ flex: 1, minWidth: 0 }}>
        <Text size="lg" role="img" aria-hidden="true">
          {config.emoji}
        </Text>
        <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs">
            <Badge color={config.color} variant="light" size="xs">
              {config.label}
            </Badge>
            {!alert.leido && (
              <Badge color="red" variant="dot" size="xs">
                Nueva
              </Badge>
            )}
          </Group>
          <Text size="xs" c="dimmed" lineClamp={2}>
            {alert.mensaje}
          </Text>
          <Text fz={10} c="dimmed">
            {new Date(alert.created_at).toLocaleDateString("es-AR", {
              day: "2-digit",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Text>
        </Stack>
      </Group>
      {!alert.leido && (
        <Tooltip label="Marcar como leída">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            radius="md"
            loading={isPending}
            onClick={() => markRead(alert.id)}
            aria-label="Marcar alerta como leída"
          >
            <IconCheck size={14} />
          </ActionIcon>
        </Tooltip>
      )}
    </Group>
  );
}

interface AlertCenterProps {
  opened: boolean;
  onClose: () => void;
}

export function AlertCenter({ opened, onClose }: AlertCenterProps) {
  const { data: unread, isLoading: loadingUnread } = useSmartAlerts({
    leido: false,
    page_size: 20,
  });
  const { data: read, isLoading: loadingRead } = useSmartAlerts({
    leido: true,
    page_size: 10,
  });
  const { mutate: markRead, isPending: isMarkingAll } = useMarkAlertRead();

  const unreadItems = unread?.data ?? [];
  const readItems = read?.data ?? [];
  const unreadCount = unread?.meta.total ?? 0;
  const isLoading = loadingUnread || loadingRead;

  function markAllRead() {
    for (const alert of unreadItems) {
      markRead(alert.id);
    }
  }

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="sm">
          <Text fw={600} fz={15}>
            Centro de Alertas
          </Text>
          {unreadCount > 0 && (
            <Badge color="red" size="sm" variant="filled" aria-label={`${unreadCount} sin leer`}>
              {unreadCount}
            </Badge>
          )}
        </Group>
      }
      position="right"
      size="sm"
      padding="md"
    >
      <Stack gap="md">
        {unreadCount > 0 && (
          <Group justify="flex-end">
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              leftSection={<IconCheck size={12} />}
              loading={isMarkingAll}
              onClick={markAllRead}
              aria-label="Marcar todas las alertas como leídas"
            >
              Marcar todas leídas
            </Button>
          </Group>
        )}

        {isLoading ? (
          <Stack gap="xs">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} height={72} radius="sm" />
            ))}
          </Stack>
        ) : (
          <>
            {/* Unread */}
            {unreadItems.length > 0 && (
              <Stack gap={4}>
                <Text
                  fz={11}
                  fw={600}
                  c="dimmed"
                  tt="uppercase"
                  style={{ letterSpacing: "0.04em" }}
                >
                  Sin leer ({unreadCount})
                </Text>
                {unreadItems.map((a) => (
                  <AlertItem key={a.id} alert={a} />
                ))}
              </Stack>
            )}

            {/* Read */}
            {readItems.length > 0 && (
              <Stack gap={4}>
                <Text
                  fz={11}
                  fw={600}
                  c="dimmed"
                  tt="uppercase"
                  style={{ letterSpacing: "0.04em" }}
                >
                  Leídas
                </Text>
                {readItems.map((a) => (
                  <AlertItem key={a.id} alert={a} />
                ))}
              </Stack>
            )}

            {unreadItems.length === 0 && readItems.length === 0 && (
              <Stack align="center" gap="xs" py="xl">
                <Text size="xl" role="img" aria-hidden="true">
                  🔔
                </Text>
                <IconBellOff size={32} color="var(--mantine-color-dimmed)" />
                <Text size="sm" c="dimmed" ta="center">
                  No hay alertas todavía.
                </Text>
              </Stack>
            )}
          </>
        )}
      </Stack>
    </Drawer>
  );
}
