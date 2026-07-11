/** Estado de stock por artículo (F3 multi-rubro) — lógica pura para la vista Inventario. */

export type EstadoStock = "sin_stock" | "bajo" | "ok";

export function estadoStock(stock: number, stockMinimo: number): EstadoStock {
  if (stock <= 0) return "sin_stock";
  if (stock <= stockMinimo) return "bajo";
  return "ok";
}

/** Presentación del estado (Badge de Mantine). */
export const ESTADO_STOCK_UI: Record<EstadoStock, { label: string; color: string }> = {
  sin_stock: { label: "Sin stock", color: "red" },
  bajo: { label: "Stock bajo", color: "yellow" },
  ok: { label: "OK", color: "green" },
};
