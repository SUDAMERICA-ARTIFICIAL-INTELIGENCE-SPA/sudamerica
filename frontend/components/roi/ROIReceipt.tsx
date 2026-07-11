"use client";

import { CHART_COLORS } from "@/lib/chart-config";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import { Divider, Group, Paper, Stack, Text } from "@mantine/core";
import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";

interface AnimatedValueProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  color?: string;
  size?: string;
}

function AnimatedValue({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  color,
  size = "28px",
}: AnimatedValueProps) {
  const spring = useSpring(0, { damping: 30, stiffness: 80 });
  const display = useTransform(spring, (v) => `${prefix}${v.toFixed(decimals)}${suffix}`);

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  return (
    <motion.span
      style={{
        color: color ?? "var(--mantine-color-text)",
        fontSize: size,
        fontWeight: 700,
        lineHeight: 1.1,
        fontFamily: TYPOGRAPHY.kpiNumber.fontFamily,
        fontVariantNumeric: TYPOGRAPHY.kpiNumber.fontVariantNumeric,
      }}
      aria-live="polite"
    >
      {display}
    </motion.span>
  );
}

interface ReceiptLineProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  color?: string;
  bold?: boolean;
}

function ReceiptLine({
  label,
  value,
  prefix = "$",
  suffix = "",
  decimals = 0,
  color,
  bold = false,
}: ReceiptLineProps) {
  return (
    <Group justify="space-between" align="center" py={4}>
      <Text size="sm" fw={bold ? 600 : 400} {...(bold ? {} : { c: "dimmed" })}>
        {label}
      </Text>
      <AnimatedValue
        value={value}
        prefix={prefix}
        suffix={suffix}
        decimals={decimals}
        size={bold ? "20px" : "15px"}
        {...(color ? { color } : {})}
      />
    </Group>
  );
}

export interface ROIReceiptData {
  timeSavedUsd: number;
  incrementalRevenue: number;
  totalBenefit: number;
  saasPrice: number;
  netRoi: number;
  roiPercent: number;
  hoursSaved: number;
  efficiencyGain: number;
}

interface ROIReceiptProps {
  data: ROIReceiptData;
}

export function ROIReceipt({ data }: ROIReceiptProps) {
  const isPositive = data.roiPercent >= 0;

  return (
    <Paper
      p="xl"
      radius="md"
      shadow="md"
      style={{
        border: "2px solid var(--mantine-color-indigo-light)",
        position: "relative",
        overflow: "hidden",
      }}
      aria-label="Recibo de Valor — ROI Calculator"
    >
      {/* Decorative stripe */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: `linear-gradient(90deg, var(--mantine-color-indigo-6), ${CHART_COLORS.secondary})`,
        }}
        aria-hidden="true"
      />

      <Stack gap="xs" mt={8}>
        {/* Header */}
        <Stack gap={2} align="center" mb="sm">
          <Text fw={700} fz={11} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.1em" }}>
            Recibo de Valor
          </Text>
          <Text fw={700} fz={18} c="indigo">
            Sudamérica AI
          </Text>
        </Stack>

        <Divider variant="dashed" />

        {/* Benefits */}
        <Stack gap={2} mt="xs">
          <Text fz={10} fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.05em" }}>
            Beneficios generados
          </Text>
          <ReceiptLine label="⏱ Tiempo ahorrado" value={data.timeSavedUsd} />
          <ReceiptLine label="📈 Ventas incrementales" value={data.incrementalRevenue} />
        </Stack>

        <Divider />

        <ReceiptLine label="Total beneficios" value={data.totalBenefit} bold />

        <Divider />

        {/* Costs */}
        <Stack gap={2}>
          <Text fz={10} fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.05em" }}>
            Inversión
          </Text>
          <ReceiptLine label="Suscripción Sudamérica AI" value={data.saasPrice} />
        </Stack>

        <Divider />

        {/* Net ROI */}
        <ReceiptLine
          label="Beneficio neto"
          value={data.netRoi}
          bold
          color={isPositive ? "var(--mantine-color-green-6)" : "var(--mantine-color-red-6)"}
        />

        <Divider variant="dashed" />

        {/* Big ROI number */}
        <Stack align="center" gap={4} py="sm">
          <Text fz={11} fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }}>
            Retorno sobre inversión
          </Text>
          <AnimatedValue
            value={data.roiPercent}
            suffix="%"
            decimals={0}
            color={isPositive ? "var(--mantine-color-green-6)" : "var(--mantine-color-red-6)"}
            size="48px"
          />
          <Text fz={12} c="dimmed">
            por cada $1 invertido
          </Text>
        </Stack>

        <Divider variant="dashed" />

        {/* Secondary metrics */}
        <SimpleMetrics hoursSaved={data.hoursSaved} efficiencyGain={data.efficiencyGain} />
      </Stack>
    </Paper>
  );
}

function SimpleMetrics({
  hoursSaved,
  efficiencyGain,
}: {
  hoursSaved: number;
  efficiencyGain: number;
}) {
  return (
    <Group justify="space-around" py="xs">
      <Stack gap={2} align="center">
        <AnimatedValue
          value={hoursSaved}
          suffix="h"
          decimals={0}
          color="var(--mantine-color-indigo-6)"
          size="22px"
        />
        <Text fz={10} c="dimmed" ta="center">
          horas ahorradas
        </Text>
      </Stack>
      <Stack gap={2} align="center">
        <AnimatedValue
          value={efficiencyGain}
          suffix="%"
          decimals={0}
          color="var(--mantine-color-yellow-6)"
          size="22px"
        />
        <Text fz={10} c="dimmed" ta="center">
          mejora en respuesta
        </Text>
      </Stack>
    </Group>
  );
}
