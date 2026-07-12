// Descubrimiento del SET VIVO de rubros por API (Fase C, Paso 6).
//
// `lib/rubros.ts` es el espejo compilado del roster de CÓDIGO (verdad-py del fixture, paridad
// py↔ts). Pero un rubro `origen='runtime'` creado por un admin NO está en ese fixture: vive solo
// en BD. Este módulo consulta `GET /api/v1/core/rubros/disponibles` (público) para traer el set
// vivo (seed+runtime activos) y lo FUSIONA sobre el baseline estático, sin degradarlo:
//   - baseline estático (RUBRO_OPTIONS) = siempre presente → si la API falla, la UI sigue
//     ofreciendo el roster de código (fail-open al baseline).
//   - set vivo de la API = fuente de verdad del set activo → añade los rubros runtime y refresca
//     labels/emoji de los seed.
// El fixture y la paridad py↔ts NO se tocan: siguen cubriendo solo el roster de código.

import { api } from "./api";
import { RUBRO_OPTIONS } from "./rubros";

/** Un rubro del set vivo tal como lo emite el backend (`RubroDisponible`, snake_case). */
export interface RubroDisponible {
  key: string;
  nombre: string;
  emoji: string;
  sector: string;
  labels: Record<string, string>;
  capacidades: string[];
  sub_entidad_label: string | null;
  recurso: boolean;
  variantes: boolean;
  precio_medida: boolean;
  categorias_semilla: string[];
}

/** Opción de selector de rubro. `value` es `string` (no `RubroKey`): el set vivo puede incluir
 *  rubros runtime que no existen en el union type compilado. */
export interface RubroOption {
  value: string;
  label: string;
  emoji: string;
}

/** Trae el set vivo de rubros (seed+runtime activos). Público: `skipAuth` (sirve onboarding/registro
 *  pre-login). Lanza `ApiError` si el backend falla; el llamador decide el fallback al baseline. */
export async function fetchRubrosDisponibles(): Promise<RubroDisponible[]> {
  return api.get<RubroDisponible[]>("/rubros/disponibles", { skipAuth: true });
}

/**
 * Fusiona el set vivo de la API sobre el baseline estático de código, preservando el orden del
 * baseline y anexando los rubros runtime nuevos al final. El baseline garantiza que el roster de
 * código siempre esté presente aunque la API falle (se llama con `live = []`).
 */
export function mergeRubroOptions(
  live: RubroDisponible[],
  baseline: readonly RubroOption[] = RUBRO_OPTIONS,
): RubroOption[] {
  const byKey = new Map<string, RubroOption>();
  for (const opt of baseline) {
    byKey.set(opt.value, { value: opt.value, label: opt.label, emoji: opt.emoji });
  }
  const orden: string[] = baseline.map((o) => o.value);
  for (const r of live) {
    if (!byKey.has(r.key)) orden.push(r.key);
    byKey.set(r.key, { value: r.key, label: r.nombre, emoji: r.emoji });
  }
  return orden.map((k) => byKey.get(k)!);
}
