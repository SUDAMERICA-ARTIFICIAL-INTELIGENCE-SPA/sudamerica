"use client";

import type { ConversationThread } from "@/hooks/useConversationThreads";
import { useConversationThreads } from "@/hooks/useConversationThreads";
import { CHART_COLORS } from "@/lib/chart-config";
import { Badge, Box, Group, Paper, Skeleton, Stack, Text, UnstyledButton } from "@mantine/core";
import { IconBrandWhatsapp, IconMessage, IconUser } from "@tabler/icons-react";

interface ConversationListProps {
  selectedLeadId: string | null;
  onSelectThread: (leadId: string, leadName?: string | null) => void;
  canalFilter?: string | undefined;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function ThreadCard({
  thread,
  isSelected,
  onClick,
}: {
  thread: ConversationThread;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <UnstyledButton onClick={onClick} w="100%">
      <Paper
        p="sm"
        radius="md"
        withBorder
        style={{
          borderColor: isSelected ? "var(--mantine-color-indigo-5)" : undefined,
          backgroundColor: isSelected ? "var(--mantine-color-indigo-light)" : undefined,
          cursor: "pointer",
          transition: "all 200ms ease-out",
        }}
      >
        <Group justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap" style={{ flex: 1, minWidth: 0 }}>
            <Box
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                backgroundColor: "var(--mantine-color-green-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {thread.last_canal === "WHATSAPP" ? (
                <IconBrandWhatsapp size={18} color={CHART_COLORS.success} />
              ) : (
                <IconUser size={18} color="var(--mantine-color-gray-6)" />
              )}
            </Box>
            <Stack gap={2} style={{ minWidth: 0 }}>
              <Group gap="xs">
                <Text size="sm" fw={600} truncate>
                  {thread.lead_name || `Lead ${thread.lead_id.slice(0, 8)}...`}
                </Text>
                <Badge size="xs" variant="light" color="gray">
                  {thread.message_count}
                </Badge>
              </Group>
              <Text size="xs" c="dimmed" truncate>
                {thread.last_role === "assistant" && "IA: "}
                {thread.last_message}
              </Text>
            </Stack>
          </Group>
          <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
            {formatRelativeTime(thread.last_message_at)}
          </Text>
        </Group>
      </Paper>
    </UnstyledButton>
  );
}

export function ConversationList({
  selectedLeadId,
  onSelectThread,
  canalFilter,
}: ConversationListProps) {
  const { data, isLoading } = useConversationThreads({
    page_size: 50,
    canal: canalFilter,
  });

  if (isLoading) {
    return (
      <Stack gap="xs">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={`skel-${i}`} height={64} radius="md" />
        ))}
      </Stack>
    );
  }

  const threads = data?.data ?? [];

  if (threads.length === 0) {
    return (
      <Stack align="center" gap="xs" py="xl">
        <IconMessage size={40} color="var(--mantine-color-gray-4)" />
        <Text size="sm" c="dimmed">
          Sin conversaciones aún
        </Text>
        <Text size="xs" c="dimmed">
          Conecta WhatsApp para empezar a recibir mensajes
        </Text>
      </Stack>
    );
  }

  return (
    <Stack gap="xs">
      {threads.map((thread) => (
        <ThreadCard
          key={thread.lead_id}
          thread={thread}
          isSelected={selectedLeadId === thread.lead_id}
          onClick={() => onSelectThread(thread.lead_id, thread.lead_name)}
        />
      ))}
    </Stack>
  );
}
