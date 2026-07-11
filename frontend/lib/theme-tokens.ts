// ══════════════════════════════════════════════════════════════════════════
// Design System — Premium Dark (pre-Apple) visual tokens (SSOT)
//
// Single source of truth del look "oscuro por defecto" original del repo
// (dark default + acento índigo #4C6EF5 + dark glass & glow + Inter + 12px).
// `app/layout.tsx` consume estos tokens para armar el theme de Mantine;
// `app/globals.css` espeja los mismos hex/rgba en selectores que el theme no
// alcanza (glass, glow, focus ring). Mantener los tres en sincronía.
// ══════════════════════════════════════════════════════════════════════════

import type { MantineColorsTuple } from "@mantine/core";

/**
 * Alias-compat (decisión Fase 0 del revert estético): el color Mantine sigue
 * registrado como `appleBlue` para no tocar sus ~11 referencias externas
 * (`color="appleBlue"`, `--mantine-color-appleBlue-*`), pero la tupla son los
 * shades ÍNDIGO de Mantine/Open Color. Shade 6 (`#4C6EF5`) = acento canónico.
 */
export const APPLE_BLUE: MantineColorsTuple = [
  "#EDF2FF",
  "#DBE4FF",
  "#BAC8FF",
  "#91A7FF",
  "#748FFC",
  "#5C7CFA",
  "#4C6EF5",
  "#4263EB",
  "#3B5BDB",
  "#364FC6",
];

/** Paleta dark azul-pizarra original (pre-Apple, de layout.tsx@409b3d4). */
export const DARK_NEUTRAL: MantineColorsTuple = [
  "#C9CACD",
  "#AEAFB5",
  "#8E9099",
  "#636571",
  "#484B58",
  "#353845",
  "#282A36",
  "#1E2029",
  "#161820",
  "#0E1017",
];

/** Canonical accent color — índigo (espeja `APPLE_BLUE[6]` vía alias-compat). */
export const ACCENT = "#4C6EF5" as const;

export const LIGHT = {
  background: "#F9FAFB",
  surface: "#FFFFFF",
  text: "#212529",
  textSecondary: "#868E96",
  hairline: "rgba(0, 0, 0, 0.08)",
  glassBackground: "rgba(255, 255, 255, 0.9)",
} as const;

export const DARK = {
  background: "#0E1017",
  surface: "#1E2029",
  text: "#C9CACD",
  textSecondary: "#8E9099",
  hairline: "rgba(255, 255, 255, 0.06)",
  glassBackground: "rgba(22, 24, 35, 0.92)",
} as const;

export const SEMANTIC = {
  success: "#37B24D",
  warning: "#F08C00",
  danger: "#E03131",
  /**
   * Success color for body text on a surface — `SEMANTIC.success` como texto
   * sobre blanco no pasa WCAG AA; esto lo oscurece solo en light mode,
   * conservando el acento vibrante para usos no-texto (badges, icons, dots).
   */
  successText: "light-dark(#2B8A3E, #37B24D)",
} as const;

/** Corner radii (px) — used for both Mantine `theme.radius` and raw CSS. */
export const RADIUS = {
  /** Radio de las filas del nav — el del sidebar de prod (standalone @4c77479). */
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
} as const;

/** Sombras densas pre-Apple (layout.tsx@409b3d4) — se aplican en ambos schemes. */
export const SHADOWS_LIGHT = {
  xs: "0 1px 2px rgba(0, 0, 0, 0.15)",
  sm: "0 1px 3px rgba(0, 0, 0, 0.2), 0 1px 2px rgba(0, 0, 0, 0.15)",
  md: "0 4px 8px rgba(0, 0, 0, 0.25), 0 2px 4px rgba(0, 0, 0, 0.15)",
  lg: "0 10px 20px rgba(0, 0, 0, 0.3), 0 4px 8px rgba(0, 0, 0, 0.15)",
  xl: "0 20px 40px rgba(0, 0, 0, 0.35), 0 8px 16px rgba(0, 0, 0, 0.15)",
} as const;

/** Variante dark, un punto más densa (sm = cardShadowDark pre-Apple exacto). */
export const SHADOWS_DARK = {
  xs: "0 1px 2px rgba(0, 0, 0, 0.25)",
  sm: "0 2px 8px rgba(0, 0, 0, 0.4), 0 1px 3px rgba(0, 0, 0, 0.3)",
  md: "0 4px 12px rgba(0, 0, 0, 0.45), 0 2px 4px rgba(0, 0, 0, 0.3)",
  lg: "0 10px 24px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3)",
  xl: "0 24px 48px rgba(0, 0, 0, 0.55), 0 8px 16px rgba(0, 0, 0, 0.3)",
} as const;

/**
 * Dark glass base (globals.css@41d1377). Consumidor real: CommandPalette.
 * navbar/header/menus/notifications tienen sus PROPIOS rgba en globals.css
 * (byte-fieles a 41d1377, cada superficie con su valor) — editar esto NO
 * los propaga; tocar globals.css directamente para esas superficies.
 */
export const GLASS = {
  light: { background: LIGHT.glassBackground, backdropFilter: "blur(16px)" },
  dark: { background: DARK.glassBackground, backdropFilter: "blur(24px) saturate(180%)" },
} as const;

/** Motion — transiciones 200ms ease del design system original. */
export const MOTION = {
  durationFast: "200ms",
  durationBase: "200ms",
  durationSlow: "300ms",
  easing: "ease",
} as const;

/**
 * Typographic scale for page-level chrome (page titles, KPI numbers, section
 * labels, body copy). Todo en Inter (`--font-inter`, next/font en layout.tsx);
 * sin display font separada (Geist eliminada con el revert pre-Apple).
 */
export const TYPOGRAPHY = {
  pageTitle: {
    fontFamily: "var(--font-inter), Inter, sans-serif",
    fontSize: "32px",
    fontWeight: 700,
    letterSpacing: "0",
    lineHeight: 1.2,
  },
  kpiNumber: {
    fontFamily: "var(--font-inter), Inter, sans-serif",
    fontSize: "40px",
    fontWeight: 700,
    fontVariantNumeric: "tabular-nums",
    lineHeight: 1.1,
  },
  sectionLabel: {
    fontSize: "11px",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  body: {
    fontSize: "14px",
    fontWeight: 400,
    lineHeight: 1.5,
  },
} as const;

/** Sticky topbar height (px) — shared by the AppShell `header` config and CSS `calc()` offsets. */
export const HEADER_HEIGHT = 56 as const;

/** Sidebar navbar width (px) — shared by the AppShell `navbar` config. */
export const SIDEBAR_WIDTH = 296 as const;

/** Max width (px) of the centered content container inside `AppShell.Main`. */
export const CONTENT_MAX_WIDTH = 1360 as const;

export type ThemeTokens = {
  accent: string;
  light: typeof LIGHT;
  dark: typeof DARK;
  semantic: typeof SEMANTIC;
  radius: typeof RADIUS;
};
