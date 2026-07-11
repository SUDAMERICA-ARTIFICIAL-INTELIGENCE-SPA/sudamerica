"use client";

import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { ActionIcon, Group, Paper, Skeleton, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface KpiCardProps {
  title: string;
  value: number;
  isLoading?: boolean;
  /** Percentage change vs previous period */
  trend?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  description?: string;
  color?: string;
  icon?: ReactNode;
}

export function KpiCard({
  title,
  value,
  isLoading,
  trend,
  prefix = "",
  suffix = "",
  decimals = 0,
  description,
  color = "indigo",
  icon,
}: KpiCardProps) {
  if (isLoading) {
    return (
      <Paper p="lg" radius="md" shadow="sm">
        <Stack gap="xs">
          <Skeleton height={14} width="60%" radius="sm" />
          <Skeleton height={38} width="75%" radius="sm" />
          <Skeleton height={12} width="40%" radius="sm" />
        </Stack>
      </Paper>
    );
  }

  const trendPositive = trend !== undefined && trend >= 0;
  const trendLabel = trend !== undefined ? `${trendPositive ? "+" : ""}${trend.toFixed(1)}%` : null;

  return (
    <Paper
      p="lg"
      radius="md"
      shadow="sm"
      style={{
        borderTop: `2px solid var(--mantine-color-${color}-5)`,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle color glow behind the card */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 60,
          background: `radial-gradient(ellipse at 50% 0%, var(--mantine-color-${color}-light), transparent 80%)`,
          opacity: 0.4,
          pointerEvents: "none",
        }}
      />
      <Stack gap="xs" style={{ position: "relative" }}>
        <Group justify="space-between" align="center">
          <Text
            size="sm"
            c="dimmed"
            fw={500}
            tt="uppercase"
            style={{ letterSpacing: "0.04em", fontSize: "11px" }}
          >
            {title}
          </Text>
          {icon && (
            <ActionIcon variant="light" color={color} size="md" aria-label={title} radius="md">
              {icon}
            </ActionIcon>
          )}
        </Group>

        <Text
          fw={700}
          style={{ fontSize: "36px", lineHeight: 1.1 }}
          aria-label={`${title}: ${prefix}${value}${suffix}`}
        >
          <AnimatedNumber value={value} prefix={prefix} suffix={suffix} decimals={decimals} />
        </Text>

        {(trendLabel !== null || description) && (
          <Group gap={6} align="center">
            {trendLabel !== null && (
              <Text
                size="xs"
                fw={600}
                c={trendPositive ? "green" : "red"}
                aria-label={`Variación: ${trendLabel}`}
              >
                {trendLabel}
              </Text>
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
