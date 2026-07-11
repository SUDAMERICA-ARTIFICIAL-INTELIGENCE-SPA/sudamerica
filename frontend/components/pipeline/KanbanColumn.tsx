"use client";

import { LeadCard } from "@/components/pipeline/LeadCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { LeadEstado } from "@/lib/enums";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import type { Lead } from "@/lib/types";
import { Badge, Group, Paper, ScrollArea, Skeleton, Stack, Text } from "@mantine/core";

const ESTADO_LABELS: Record<LeadEstado, string> = {
  NUEVO: "Nuevo",
  CONTACTADO: "Contactado",
  EN_PROCESO: "En Proceso",
  CONVERTIDO: "Convertido",
  DESCARTADO: "Descartado",
};

const ESTADO_COLORS: Record<LeadEstado, string> = {
  NUEVO: "blue",
  CONTACTADO: "cyan",
  EN_PROCESO: "indigo",
  CONVERTIDO: "green",
  DESCARTADO: "red",
};

interface KanbanColumnProps {
  estado: LeadEstado;
  leads: Lead[];
  isLoading?: boolean;
  onLeadClick: (lead: Lead) => void;
}

function formatCurrency(value: number) {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value}`;
}

export function KanbanColumn({ estado, leads, isLoading, onLeadClick }: KanbanColumnProps) {
  const totalValue = leads.reduce((sum, l) => sum + (l.valor_estimado ?? 0), 0);
  const color = ESTADO_COLORS[estado];
  const label = ESTADO_LABELS[estado];

  return (
    <Stack
      gap="sm"
      style={{ minWidth: 240, maxWidth: 280, flex: "0 0 260px" }}
      aria-label={`Columna: ${label}`}
    >
      {/* Column Header */}
      <Paper
        p="sm"
        radius="md"
        style={{
          backgroundColor: `var(--mantine-color-${color}-light)`,
          border: `1px solid var(--mantine-color-${color}-light-hover)`,
        }}
      >
        <Group justify="space-between" align="center">
          <Group gap="xs" align="center">
            <Badge color={color} variant="filled" size="xs" circle aria-hidden="true">
              {leads.length}
            </Badge>
            <Text
              style={{
                ...TYPOGRAPHY.sectionLabel,
                color: `var(--mantine-color-${color}-light-color)`,
              }}
            >
              {label}
            </Text>
          </Group>
          {totalValue > 0 && (
            <Text
              size="xs"
              c="dimmed"
              fw={500}
              aria-label={`Valor total: ${formatCurrency(totalValue)}`}
            >
              {formatCurrency(totalValue)}
            </Text>
          )}
        </Group>
      </Paper>

      {/* Lead Cards */}
      <ScrollArea h={560} scrollbarSize={4}>
        {isLoading ? (
          <Stack gap="sm">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} height={88} radius="md" />
            ))}
          </Stack>
        ) : leads.length === 0 ? (
          <EmptyState icon="📭" title="Sin leads" description={`No hay leads en estado ${label}`} />
        ) : (
          <Stack gap="sm" pb="sm">
            {leads.map((lead) => (
              <LeadCard key={lead.id} lead={lead} onClick={onLeadClick} />
            ))}
          </Stack>
        )}
      </ScrollArea>
    </Stack>
  );
}
