"use client";

import { ScoreThermometer } from "@/components/ui/ScoreThermometer";
import { CHART_COLORS } from "@/lib/chart-config";
import { LeadCanal } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import { Badge, Group, Paper, Stack, Text, UnstyledButton } from "@mantine/core";
import {
  IconBrandFacebook,
  IconBrandInstagram,
  IconBrandWhatsapp,
  IconMailFilled,
  IconPhone,
  IconUserPlus,
  IconWorld,
} from "@tabler/icons-react";

const CANAL_ICON: Record<LeadCanal, React.ReactNode> = {
  [LeadCanal.WHATSAPP]: <IconBrandWhatsapp size={14} color={CHART_COLORS.success} />,
  [LeadCanal.INSTAGRAM]: <IconBrandInstagram size={14} color="var(--mantine-color-pink-6)" />,
  [LeadCanal.FACEBOOK]: <IconBrandFacebook size={14} color="var(--mantine-color-blue-6)" />,
  [LeadCanal.WEB]: <IconWorld size={14} color={CHART_COLORS.primary} />,
  [LeadCanal.TELEFONO]: <IconPhone size={14} color={CHART_COLORS.neutral} />,
  [LeadCanal.EMAIL]: <IconMailFilled size={14} color={CHART_COLORS.secondary} />,
  [LeadCanal.REFERIDO]: <IconUserPlus size={14} color={CHART_COLORS.teal} />,
};

function agingDays(createdAt: string): number {
  const diffMs = Date.now() - new Date(createdAt).getTime();
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

function AgingBadge({ days }: { days: number }) {
  const color = days >= 7 ? "red" : days >= 3 ? "yellow" : "green";
  const label = days === 0 ? "Hoy" : `${days}d`;
  return (
    <Badge color={color} variant="light" size="xs" aria-label={`Antigüedad: ${days} días`}>
      {label}
    </Badge>
  );
}

interface LeadCardProps {
  lead: Lead;
  onClick: (lead: Lead) => void;
}

export function LeadCard({ lead, onClick }: LeadCardProps) {
  const days = agingDays(lead.created_at);

  return (
    <UnstyledButton
      onClick={() => onClick(lead)}
      aria-label={`Lead: ${lead.nombre}`}
      style={{ display: "block", width: "100%", textAlign: "left" }}
    >
      <Paper
        p="sm"
        radius="md"
        shadow="sm"
        style={{
          transition: "box-shadow 200ms ease-out, transform 200ms ease-out",
          cursor: "pointer",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--mantine-shadow-md)";
          (e.currentTarget as HTMLDivElement).style.transform = "translateY(-1px)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = "";
          (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
        }}
      >
        <Stack gap={8}>
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Text fw={600} size="sm" lineClamp={1} style={{ flex: 1 }}>
              {lead.nombre}
            </Text>
            <Group gap={4} wrap="nowrap" aria-label={`Canal: ${lead.canal}`}>
              {CANAL_ICON[lead.canal]}
            </Group>
          </Group>

          {lead.valor_estimado !== null && (
            <Text size="sm" fw={500} c="indigo">
              $
              {Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(lead.valor_estimado)}
            </Text>
          )}

          <Group justify="space-between" align="center">
            <AgingBadge days={days} />
            <ScoreThermometer score={lead.ai_score} />
          </Group>
        </Stack>
      </Paper>
    </UnstyledButton>
  );
}
