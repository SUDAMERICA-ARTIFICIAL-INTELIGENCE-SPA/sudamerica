// Shared chart palette, theme and tooltip styles for Recharts + ApexCharts

import { ACCENT } from "@/lib/theme-tokens";

// primary now mirrors the Apple-blue accent (theme-tokens ACCENT). secondary/gold were
// a shouting orange-red + amber pair (#FF6B35/#F59F00) that clashed with the new sober
// palette — replaced with a muted Apple system-orange and a desaturated gold/mustard
// so categorical series stay distinguishable without the visual noise.
export const CHART_COLORS = {
  primary: ACCENT,
  secondary: "#FF9F0A",
  gold: "#C9A227",
  success: "#37B24D",
  warning: "#F08C00",
  danger: "#E03131",
  neutral: "#868E96",
  purple: "#9C36B5",
  teal: "#0CA678",
} as const;

export const CHART_PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.secondary,
  CHART_COLORS.gold,
  CHART_COLORS.success,
  CHART_COLORS.purple,
  CHART_COLORS.teal,
  CHART_COLORS.warning,
  CHART_COLORS.danger,
] as const;

/** Light-mode tooltip style — components should use getTooltipStyle() for dark-mode awareness */
export const RECHARTS_DEFAULTS = {
  margin: { top: 8, right: 16, bottom: 8, left: 8 },
  tooltipStyle: {
    backgroundColor: "var(--mantine-color-body)",
    border: "1px solid var(--mantine-color-default-border)",
    borderRadius: "8px",
    padding: "8px 12px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    fontSize: "13px",
    color: "var(--mantine-color-text)",
  },
  gridStyle: {
    stroke: "var(--mantine-color-default-border)",
    strokeDasharray: "3 3",
  },
  axisStyle: {
    tick: { fontSize: 12, fill: CHART_COLORS.neutral },
  },
} as const;

export const APEXCHARTS_DEFAULTS = {
  chart: {
    background: "transparent",
    fontFamily: "Inter, sans-serif",
    toolbar: { show: false },
    animations: {
      enabled: true,
      speed: 400,
    },
  },
  tooltip: {
    theme: "dark",
    style: { fontFamily: "Inter, sans-serif" },
  },
  grid: {
    borderColor: "var(--mantine-color-default-border)",
    strokeDashArray: 3,
  },
  states: {
    hover: { filter: { type: "lighten", value: 0.05 } },
    active: { filter: { type: "darken", value: 0.1 } },
  },
  dataLabels: { enabled: false },
} as const;

export type ChartColor = (typeof CHART_COLORS)[keyof typeof CHART_COLORS];
