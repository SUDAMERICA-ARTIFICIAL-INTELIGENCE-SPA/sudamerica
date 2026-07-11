"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useAccionarRevision, useRevisionHumana } from "@/hooks/useRevisionHumana";
import { RevisionAccion } from "@/lib/enums";
import type { RevisionHumana } from "@/lib/types";
import { ActionIcon, Badge, Group, Paper, Skeleton, Stack, Text, Tooltip } from "@mantine/core";
import { IconCheck, IconEdit, IconX } from "@tabler/icons-react";

function RevisionCard({ revision }: { revision: RevisionHumana }) {
  const { mutate: accionar, isPending } = useAccionarRevision();

  function handle(accion: RevisionAccion) {
    accionar({ id: revision.id, accion });
  }

  const createdAt = new Date(revision.created_at).toLocaleString("es-AR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <Paper
      p="sm"
      radius="md"
      withBorder
      aria-label={`Revisión pendiente — conversación ${revision.conversation_id.slice(0, 8)}`}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap={4} style={{ flex: 1 }}>
          <Group gap="xs">
            <Badge color="orange" variant="light" size="xs">
              Pendiente
            </Badge>
            <Text size="xs" c="dimmed">
              Conv. #{revision.conversation_id.slice(0, 8)}
            </Text>
          </Group>
          <Text size="xs" c="dimmed">
            Recibido: {createdAt}
          </Text>
        </Stack>

        <Group gap="xs">
          <Tooltip label="Aprobar">
            <ActionIcon
              color="green"
              variant="light"
              size="sm"
              loading={isPending}
              onClick={() => handle(RevisionAccion.APROBAR)}
              aria-label="Aprobar revisión"
              radius="md"
            >
              <IconCheck size={14} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Editar">
            <ActionIcon
              color="blue"
              variant="light"
              size="sm"
              loading={isPending}
              onClick={() => handle(RevisionAccion.EDITAR)}
              aria-label="Editar revisión"
              radius="md"
            >
              <IconEdit size={14} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Rechazar">
            <ActionIcon
              color="red"
              variant="light"
              size="sm"
              loading={isPending}
              onClick={() => handle(RevisionAccion.RECHAZAR)}
              aria-label="Rechazar revisión"
              radius="md"
            >
              <IconX size={14} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
    </Paper>
  );
}

export function RevisionHumanaQueue() {
  const { data, isLoading } = useRevisionHumana({ pendiente: true, page_size: 10 });

  return (
    <SectionCard
      title="Cola de Revisión Humana"
      fullHeight
      action={
        data?.meta && (
          <Badge
            color="orange"
            variant="filled"
            size="xs"
            aria-label={`${data.meta.total} pendientes`}
          >
            {data.meta.total}
          </Badge>
        )
      }
    >
      {isLoading ? (
        <Stack gap="xs">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={68} radius="md" />
          ))}
        </Stack>
      ) : data?.data.length ? (
        <Stack gap="xs">
          {data.data.map((rev) => (
            <RevisionCard key={rev.id} revision={rev} />
          ))}
        </Stack>
      ) : (
        <EmptyState
          icon="✅"
          title="Sin revisiones pendientes"
          description="Todas las conversaciones han sido revisadas."
        />
      )}
    </SectionCard>
  );
}
