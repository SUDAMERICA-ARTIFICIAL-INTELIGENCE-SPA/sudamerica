"use client";

import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { ACCENT, SEMANTIC, TYPOGRAPHY } from "@/lib/theme-tokens";
import { Group, Paper, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconArrowDown, IconArrowUp } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

export interface StatCardProps {
  label: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  /** Variación porcentual vs. período anterior — renderiza flecha ↑/↓ + color semántico. */
  delta?: number;
  /** Serie mini-sparkline (sin ejes) — se omite si trae menos de 2 puntos. */
  sparklineData?: number[];
  /** Texto de apoyo bajo el número (p.ej. meta, ROI) — se omite si no viene. */
  description?: string;
  icon?: ReactNode;
  loading?: boolean;
}

const SPARKLINE_WIDTH = 100;
const SPARKLINE_HEIGHT = 28;

export function StatCard({
  label,
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  delta,
  sparklineData,
  description,
  icon,
  loading = false,
}: StatCardProps) {
  if (loading) {
    return (
      <Paper p="lg" radius="lg" shadow="sm">
        <Stack gap="xs">
          <Skeleton height={14} width="55%" radius="sm" />
          <Skeleton height={40} width="70%" radius="sm" />
          <Skeleton height={12} width="35%" radius="sm" />
        </Stack>
      </Paper>
    );
  }

  const hasDelta = delta !== undefined;
  const deltaPositive = hasDelta && delta >= 0;
  const deltaLabel = hasDelta ? `${deltaPositive ? "+" : ""}${delta.toFixed(1)}%` : null;
  const deltaColor = deltaPositive ? SEMANTIC.success : SEMANTIC.danger;
  const showSparkline = sparklineData !== undefined && sparklineData.length > 1;

  return (
    <Paper p="lg" radius="lg" shadow="sm">
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
          <Text style={TYPOGRAPHY.sectionLabel} c="dimmed">
            {label}
          </Text>
          {icon && (
            <ThemeIcon variant="light" color="gray" size="md" radius="md" aria-hidden="true">
              {icon}
            </ThemeIcon>
          )}
        </Group>

        <Group justify="space-between" align="flex-end" wrap="nowrap" gap="sm">
          <Text style={TYPOGRAPHY.kpiNumber} aria-label={`${label}: ${prefix}${value}${suffix}`}>
            {typeof value === "number" ? (
              <AnimatedNumber value={value} prefix={prefix} suffix={suffix} decimals={decimals} />
            ) : (
              `${prefix}${value}${suffix}`
            )}
          </Text>

          {showSparkline && (
            <div
              style={{ width: SPARKLINE_WIDTH, height: SPARKLINE_HEIGHT, flexShrink: 0 }}
              aria-hidden="true"
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sparklineData.map((v) => ({ v }))}>
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke={ACCENT}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Group>

        {(deltaLabel !== null || description) && (
          <Group gap={6} align="center">
            {deltaLabel !== null && (
              <Group gap={4} align="center" wrap="nowrap">
                {deltaPositive ? (
                  <IconArrowUp size={14} color={deltaColor} aria-hidden="true" />
                ) : (
                  <IconArrowDown size={14} color={deltaColor} aria-hidden="true" />
                )}
                <Text size="xs" fw={600} c={deltaColor} aria-label={`Variación: ${deltaLabel}`}>
                  {deltaLabel}
                </Text>
              </Group>
            )}
            {description && (
              <Text size="xs" c="dimmed">
                {description}
              </Text>
            )}
          </Group>
        )}
      </Stack>
    </Paper>
  );
}
