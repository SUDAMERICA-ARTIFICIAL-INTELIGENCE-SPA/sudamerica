import { Badge, Group, Text } from "@mantine/core";

interface ScoreThermometerProps {
  score: number | null;
  showLabel?: boolean;
}

function getScoreConfig(score: number) {
  if (score >= 85) return { emoji: "🔥", color: "red", label: "Caliente" } as const;
  if (score >= 50) return { emoji: "🟡", color: "yellow", label: "Tibio" } as const;
  return { emoji: "❄️", color: "blue", label: "Frío" } as const;
}

export function ScoreThermometer({ score, showLabel = false }: ScoreThermometerProps) {
  if (score === null || score === undefined) {
    return (
      <Text c="dimmed" size="sm" aria-label="Sin score IA">
        —
      </Text>
    );
  }

  const config = getScoreConfig(score);

  return (
    <Group gap={4} align="center" aria-label={`Score IA: ${score} — ${config.label}`}>
      <Text size="sm" role="img" aria-hidden="true">
        {config.emoji}
      </Text>
      <Badge color={config.color} variant="light" size="sm" radius="sm">
        {score}
      </Badge>
      {showLabel && (
        <Text size="xs" c="dimmed">
          {config.label}
        </Text>
      )}
    </Group>
  );
}
