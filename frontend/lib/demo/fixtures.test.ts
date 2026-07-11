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

describe("demoResolve — chokepoint determinista", () => {
  it("mapea path → fixture del rubro activo", async () => {
    const kpis = await demoResolve("/metricas/dashboard", "restaurante");
    expect(kpis).toEqual(buildDashboardKpis("restaurante"));
  });

  it("es determinista entre llamadas", async () => {
    const a = await demoResolve("/metricas/revenue?period=month", "peluqueria");
    const b = await demoResolve("/metricas/revenue?period=month", "peluqueria");
    expect(a).toEqual(b);
  });

  it("sirve tenant con el rubro en config", async () => {
    const tenant = await demoResolve<{ config: { rubro: string } }>("/tenants/me", "ferreteria");
    expect(tenant.config.rubro).toBe("ferreteria");
  });

  it("lanza error en paths no mapeados", async () => {
    await expect(demoResolve("/no/existe", "restaurante")).rejects.toThrow();
  });
});
