// ── Generador determinista de datos demo por rubro ─────────────────────────
// Semilla = hash(key [+ salt]). Sin `Math.random`/`Date.now`/`new Date()` en
// runtime (rompen SSR/tests): la aleatoriedad es un PRNG sembrado y las fechas
// son ISO precalculadas. Recargar = mismos datos (determinismo verificable).
import type { Sector } from "@/lib/sector-config";

// FNV-1a 32-bit → semilla estable a partir de un string.
function hashString(str: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

// mulberry32: PRNG rápido y determinista.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Rng {
  next(): number;
  int(min: number, max: number): number;
  float(min: number, max: number): number;
  pick<T>(items: readonly T[]): T;
  bool(p?: number): boolean;
}

/** Crea un PRNG sembrado por `key` (+ `salt` para independizar cada endpoint). */
export function makeRng(key: string, salt = ""): Rng {
  const rand = mulberry32(hashString(`${key}::${salt}`));
  const next = () => rand();
  return {
    next,
    float: (min, max) => min + (max - min) * next(),
    int: (min, max) => Math.floor(min + (max - min + 1) * next()),
    pick: <T>(items: readonly T[]): T =>
      items[Math.floor(next() * items.length) % items.length] as T,
    bool: (p = 0.5) => next() < p,
  };
}

/** Redondea a múltiplos "presentables" (miles, centenas…). */
export function roundTo(value: number, step: number): number {
  return Math.round(value / step) * step;
}

// ── Perfil económico por sector (CLP) ──────────────────────────────────────
// Escala montos/volúmenes de forma plausible: ticket alto + volumen bajo en
// automotriz/inmobiliario/b2b; ticket bajo + volumen alto en gastronomía/retail.
export interface SectorProfile {
  ticket: [number, number]; // valor promedio de transacción (CLP)
  volume: [number, number]; // transacciones/mes
  leads: [number, number]; // nuevos clientes/leads/mes
  cogsPct: [number, number]; // costo de ventas como % del revenue
}

export const SECTOR_PROFILE: Record<Sector, SectorProfile> = {
  gastronomia: {
    ticket: [8000, 16000],
    volume: [1800, 4200],
    leads: [120, 460],
    cogsPct: [0.34, 0.42],
  },
  retail: { ticket: [12000, 45000], volume: [900, 2600], leads: [90, 320], cogsPct: [0.55, 0.72] },
  salud_estetica: {
    ticket: [18000, 55000],
    volume: [240, 680],
    leads: [70, 260],
    cogsPct: [0.2, 0.35],
  },
  mascotas: { ticket: [22000, 60000], volume: [180, 520], leads: [60, 210], cogsPct: [0.3, 0.48] },
  automotriz: {
    ticket: [6_000_000, 28_000_000],
    volume: [8, 40],
    leads: [25, 90],
    cogsPct: [0.62, 0.8],
  },
  inmobiliario: {
    ticket: [25_000_000, 140_000_000],
    volume: [3, 14],
    leads: [18, 70],
    cogsPct: [0.55, 0.72],
  },
  b2b: { ticket: [350_000, 2_400_000], volume: [30, 140], leads: [20, 85], cogsPct: [0.4, 0.6] },
  turismo: {
    ticket: [220_000, 1_400_000],
    volume: [40, 180],
    leads: [40, 160],
    cogsPct: [0.45, 0.65],
  },
  educacion: {
    ticket: [90_000, 480_000],
    volume: [60, 260],
    leads: [55, 220],
    cogsPct: [0.25, 0.42],
  },
  otro: { ticket: [15000, 60000], volume: [200, 700], leads: [60, 220], cogsPct: [0.35, 0.55] },
};

// ── Fechas ISO precalculadas (determinista, sin new Date en runtime) ────────
// 30 días consecutivos hasta 2026-07-02 (fecha "hoy" del entorno). RevenueChart
// parsea con `new Date(fecha)` en su propio render (comportamiento existente).
export const DEMO_DATES: readonly string[] = [
  "2026-06-03",
  "2026-06-04",
  "2026-06-05",
  "2026-06-06",
  "2026-06-07",
  "2026-06-08",
  "2026-06-09",
  "2026-06-10",
  "2026-06-11",
  "2026-06-12",
  "2026-06-13",
  "2026-06-14",
  "2026-06-15",
  "2026-06-16",
  "2026-06-17",
  "2026-06-18",
  "2026-06-19",
  "2026-06-20",
  "2026-06-21",
  "2026-06-22",
  "2026-06-23",
  "2026-06-24",
  "2026-06-25",
  "2026-06-26",
  "2026-06-27",
  "2026-06-28",
  "2026-06-29",
  "2026-06-30",
  "2026-07-01",
  "2026-07-02",
];

/** Timestamps ISO fijos para created_at/reviewed_at (recientes → antiguos). */
export const DEMO_TIMESTAMPS: readonly string[] = [
  "2026-07-02T13:40:00Z",
  "2026-07-02T11:05:00Z",
  "2026-07-02T08:20:00Z",
  "2026-07-01T19:55:00Z",
  "2026-07-01T15:10:00Z",
  "2026-07-01T09:30:00Z",
  "2026-06-30T21:15:00Z",
  "2026-06-30T12:45:00Z",
];
