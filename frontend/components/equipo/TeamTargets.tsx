"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { useLeads } from "@/hooks/useLeads";
import { useSalesTargets } from "@/hooks/useSalesTargets";
import { useVentas } from "@/hooks/useVentas";
import { LeadEstado } from "@/lib/enums";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import { Group, Paper, RingProgress, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";

function currentPeriod(): string {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mm}`;
}

interface TargetCardProps {
  label: string;
  current: number;
  target: number;
  unit?: string;
  color: string;
}

function TargetCard({ label, current, target, unit = "", color }: TargetCardProps) {
  const pct = target > 0 ? Math.min(Math.round((current / target) * 100), 100) : 0;

  return (
    <Paper
      p="md"
      radius="md"
      shadow="sm"
      aria-label={`${label}: ${current}${unit} de ${target}${unit}`}
    >
      <Group gap="md" align="center">
        <RingProgress
          size={72}
          thickness={7}
          roundCaps
          sections={[{ value: pct, color }]}
          label={
            <Text ta="center" fw={700} fz={13} c={color}>
              {pct}%
            </Text>
          }
        />
        <Stack gap={2}>
          <Text fz={11} fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.04em" }}>
            {label}
          </Text>
          <Text
            style={{
              fontFamily: TYPOGRAPHY.kpiNumber.fontFamily,
              fontVariantNumeric: TYPOGRAPHY.kpiNumber.fontVariantNumeric,
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 1.1,
            }}
          >
            {Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(current)}
            {unit}
          </Text>
          <Text fz={12} c="dimmed">
            meta: {Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(target)}
            {unit}
          </Text>
        </Stack>
      </Group>
    </Paper>
  );
}

export function TeamTargets() {
  const periodo = currentPeriod();
  const { data: targets, isLoading: targetsLoading } = useSalesTargets({ periodo, page_size: 1 });
  const { data: ventas, isLoading: ventasLoading } = useVentas({ page_size: 100 });
  const { data: leads, isLoading: leadsLoading } = useLeads({ page_size: 100 } as Parameters<
    typeof useLeads
  >[0]);

  const isLoading = targetsLoading || ventasLoading || leadsLoading;

  if (isLoading) {
    return (
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} height={88} radius="md" />
        ))}
      </SimpleGrid>
    );
  }

  const target = targets?.data[0];

  if (!target) {
    return (
      <Paper p="md" radius="md" shadow="sm">
        <EmptyState
          icon="🎯"
          title="Sin metas definidas"
          description={`No hay metas para ${periodo}. Configura objetivos mensuales.`}
        />
      </Paper>
    );
  }

  const ventasCount = ventas?.data.length ?? 0;
  const revenueTotal = ventas?.data.reduce((s, v) => s + v.total, 0) ?? 0;
  const leadsConvertidos =
    leads?.data.filter((l) => l.estado === LeadEstado.CONVERTIDO).length ?? 0;
  const leadsTotal = leads?.meta.total ?? 0;
  const convRate = leadsTotal > 0 ? (leadsConvertidos / leadsTotal) * 100 : 0;

  return (
    <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" aria-label="Progreso hacia metas del equipo">
      <TargetCard
        label="Revenue vs Meta"
        current={revenueTotal}
        target={target.meta_ventas}
        unit=" USD"
        color="indigo"
      />
      <TargetCard
        label="Leads vs Meta"
        current={ventasCount}
        target={target.meta_leads}
        color="teal"
      />
      <TargetCard
        label="Conversión vs Meta"
        current={Math.round(convRate)}
        target={target.meta_conversion}
        unit="%"
        color="orange"
      />
    </SimpleGrid>
  );
}
