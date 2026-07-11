"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { SectionCard } from "@/components/ui/SectionCard";
import { useAIConversations } from "@/hooks/useAIConversations";
import type { AIConversation } from "@/lib/types";
import { Badge, Group, Skeleton, Stack, Text } from "@mantine/core";

function isOffHours(dateStr: string): boolean {
  const d = new Date(dateStr);
  const hour = d.getHours();
  const day = d.getDay(); // 0=Sun, 6=Sat
  return day === 0 || day === 6 || hour < 9 || hour >= 18;
}

function formatRelative(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const diffH = Math.floor(diffMs / (1000 * 60 * 60));
  const diffD = Math.floor(diffH / 24);
  if (diffH < 1) return "hace menos de 1h";
  if (diffH < 24) return `hace ${diffH}h`;
  return `hace ${diffD}d`;
}

function InsightRow({ conv }: { conv: AIConversation }) {
  const offHours = isOffHours(conv.created_at);
  const confidence = Math.round(conv.confidence * 100);

  return (
    <Group
      py="xs"
      px="sm"
      justify="space-between"
      style={{
        borderRadius: "8px",
        backgroundColor: "var(--mantine-color-green-light)",
        borderLeft: "3px solid var(--mantine-color-green-5)",
      }}
      aria-label={`Conversación IA resuelta — confianza ${confidence}%`}
    >
      <Group gap="sm">
        <Text size="lg" role="img" aria-hidden="true">
          {offHours ? "🌙" : "✅"}
        </Text>
        <Stack gap={2}>
          <Group gap="xs">
            <Badge color="green" variant="light" size="xs">
              Resuelta
            </Badge>
            {offHours && (
              <Badge color="violet" variant="light" size="xs">
                Fuera de horario
              </Badge>
            )}
            <Badge color="gray" variant="outline" size="xs">
              Confianza {confidence}%
            </Badge>
          </Group>
          <Text size="xs" c="dimmed">
            Canal: {conv.canal} · {formatRelative(conv.created_at)}
          </Text>
        </Stack>
      </Group>
      <Text size="xs" c="dimmed" fw={500}>
        ${conv.token_cost.toFixed(3)}
      </Text>
    </Group>
  );
}

export function InsightsFeed() {
  const { data, isLoading } = useAIConversations({
    resuelto_sin_humano: true,
    page_size: 10,
  });

  return (
    <SectionCard title="Victorias de la IA" fullHeight>
      {isLoading ? (
        <Stack gap="xs">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={52} radius="sm" />
          ))}
        </Stack>
      ) : data?.data.length ? (
        <Stack gap={6}>
          {data.data.map((conv) => (
            <InsightRow key={conv.id} conv={conv} />
          ))}
        </Stack>
      ) : (
        <EmptyState
          icon="🤖"
          title="Sin victorias registradas"
          description="Las conversaciones resueltas sin humano aparecerán aquí."
        />
      )}
    </SectionCard>
  );
}
