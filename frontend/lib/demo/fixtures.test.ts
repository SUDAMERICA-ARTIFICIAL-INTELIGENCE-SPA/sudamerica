import type { RubroKey } from "@/lib/rubros";
import { describe, expect, it } from "vitest";
import {
  buildAlerts,
  buildDashboardKpis,
  buildFinancial,
  buildRevenue,
  buildTopProducts,
} from "./fixtures";
import { demoResolve } from "./resolver";

const SAMPLE: RubroKey[] = ["restaurante", "peluqueria", "ferreteria"];

describe("demo fixtures — deterministas y type-correct", () => {
  for (const key of SAMPLE) {
    describe(key, () => {
      it("DashboardKpis: determinista y coherente", () => {
        const a = buildDashboardKpis(key);
        const b = buildDashboardKpis(key);
        expect(a).toEqual(b); // recargar = mismos datos
        expect(a.ventas_mes).toBeGreaterThan(0);
        expect(a.meta_mes).toBeGreaterThan(0);
        expect(a.tasa_conversion).toBeGreaterThan(0);
        expect(a.tasa_conversion).toBeLessThanOrEqual(100);
        expect(a.ia_tasa_auto_resolucion).toBeGreaterThanOrEqual(0);
        expect(a.ia_tasa_auto_resolucion).toBeLessThanOrEqual(100);
        expect(a.ia_atendidas).toBeGreaterThanOrEqual(0);
      });

      it("Revenue: 30 puntos con fecha ISO y valores positivos", () => {
        const rev = buildRevenue(key);
        expect(rev).toHaveLength(30);
        for (const p of rev) {
          expect(p.fecha).toMatch(/^\d{4}-\d{2}-\d{2}$/);
          expect(p.revenue_real).toBeGreaterThan(0);
          expect(p.revenue_forecast).toBeGreaterThan(0);
        }
      });

      it("TopProducts: respeta el límite y viene ordenado por revenue desc", () => {
        const top = buildTopProducts(key, 5);
        expect(top.length).toBeGreaterThan(0);
        expect(top.length).toBeLessThanOrEqual(5);
        const revenues = top.map((p) => p.revenue);
        expect(revenues).toEqual([...revenues].sort((a, b) => b - a));
      });

      it("Financial: márgenes consistentes con revenue/cogs", () => {
        const f = buildFinancial(key);
        expect(f.revenue).toBeGreaterThan(0);
        expect(f.cogs).toBeLessThanOrEqual(f.revenue);
        expect(f.margen_bruto).toBe(f.revenue - f.cogs);
      });

      it("Alerts: paginado con mensaje rubro-teñido no vacío", () => {
        const alerts = buildAlerts(key, 8);
        expect(alerts.data.length).toBeLessThanOrEqual(alerts.meta.total);
        for (const alert of alerts.data) {
          expect(alert.mensaje.length).toBeGreaterThan(0);
          expect(alert.leido).toBe(false);
        }
      });
    });
  }
});

describe("demoResolve — chokepoint snapshot-first", () => {
  it("héroe cosmetica_belleza: sirve el snapshot REAL (KPIs del backend seedeado)", async () => {
    const kpis = await demoResolve<{ ventas_mes: number }>(
      "/metricas/dashboard",
      "cosmetica_belleza",
    );
    // Valor capturado del backend seedeado (ver metricas-dashboard.json). No es
    // el builder sintético — es el dato real de aura-demo.
    expect(kpis.ventas_mes).toBe(557800);
  });

  it("otro rubro: reskin determinista del snapshot (no lanza, mismas cifras entre llamadas)", async () => {
    const a = await demoResolve<{ ventas_mes: number }>("/metricas/dashboard", "restaurante");
    const b = await demoResolve<{ ventas_mes: number }>("/metricas/dashboard", "restaurante");
    expect(a).toEqual(b);
    expect(a.ventas_mes).toBeGreaterThan(0);
  });

  it("cubre endpoints OLA B sin fixture-faltante (compras paginado)", async () => {
    const ordenes = await demoResolve<{ data: unknown[]; meta: { total: number } }>(
      "/compras/ordenes?page=1&page_size=10",
      "cosmetica_belleza",
    );
    expect(Array.isArray(ordenes.data)).toBe(true);
    expect(ordenes.data.length).toBeLessThanOrEqual(10);
    expect(ordenes.meta.total).toBeGreaterThan(0);
  });

  it("re-pagina el snapshot según page/page_size", async () => {
    const p1 = await demoResolve<{ data: unknown[]; meta: { total: number; total_pages: number } }>(
      "/leads?page=1&page_size=5",
      "cosmetica_belleza",
    );
    expect(p1.data.length).toBe(5);
    expect(p1.meta.total_pages).toBe(Math.ceil(p1.meta.total / 5));
  });

  it("sirve tenant con el rubro en config", async () => {
    const tenant = await demoResolve<{ config: { rubro: string } }>("/tenants/me", "ferreteria");
    expect(tenant.config.rubro).toBe("ferreteria");
  });

  it("path desconocido → sobre vacío (la vitrina nunca crashea)", async () => {
    const res = await demoResolve<{ data: unknown[]; meta: { total: number } }>(
      "/no/existe",
      "restaurante",
    );
    expect(res.data).toEqual([]);
    expect(res.meta.total).toBe(0);
  });
});
