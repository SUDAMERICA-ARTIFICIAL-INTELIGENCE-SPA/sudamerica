import { Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  /** Emoji (string) o ícono sobrio (p.ej. Tabler `<IconInbox size={40} />`) — ambos se atenúan a gris. */
  icon?: ReactNode;
  title: string;
  description?: string;
  /** CTA opcional, p.ej. un `<Button>`. */
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Stack align="center" justify="center" gap="md" py="xl" aria-label={`Estado vacío: ${title}`}>
      {icon && (
        <Text size="3rem" c="dimmed" role="img" aria-hidden="true">
          {icon}
        </Text>
      )}
      <Stack align="center" gap="xs">
        <Title order={4} c="dimmed">
          {title}
        </Title>
        {description && (
          <Text size="sm" c="dimmed" ta="center" maw={400}>
            {description}
          </Text>
        )}
      </Stack>
      {action}
    </Stack>
  );
}
