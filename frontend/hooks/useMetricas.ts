"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  DashboardKpis,
  FinancialSummary,
  MenuEngineeringItem,
  OperationalSummary,
  RevenueDataPoint,
  TopProduct,
  WeeklyActivityPoint,
} from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function useDashboardKpis() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "dashboard", { tenantId }],
    queryFn: () => api.get<DashboardKpis>("/metricas/dashboard"),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useOperationalSummary(period: "day" | "week" | "month" = "day") {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "operativo", { tenantId, period }],
    queryFn: () => api.get<OperationalSummary>(`/metricas/operativo?period=${period}`),
    enabled: !!tenantId,
    refetchInterval: period === "day" ? 60_000 : 5 * 60 * 1000,
  });
}

export function useRevenueData(period: "day" | "week" | "month" = "month") {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "revenue", { tenantId, period }],
    queryFn: () => api.get<RevenueDataPoint[]>(`/metricas/revenue?period=${period}`),
    enabled: !!tenantId,
  });
}

export function useTopProducts(period: "day" | "week" | "month" = "day", limit = 5) {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "productos-top", { tenantId, period, limit }],
    queryFn: () => api.get<TopProduct[]>(`/metricas/productos-top?period=${period}&limit=${limit}`),
    enabled: !!tenantId,
  });
}

export function useFinancialSummary(period: "day" | "week" | "month" = "month") {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "financiero", { tenantId, period }],
    queryFn: () => api.get<FinancialSummary>(`/metricas/financiero?period=${period}`),
    enabled: !!tenantId,
  });
}

export function useMenuEngineering(period: "day" | "week" | "month" = "month") {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "menu-engineering", { tenantId, period }],
    queryFn: () => api.get<MenuEngineeringItem[]>(`/metricas/menu-engineering?period=${period}`),
    enabled: !!tenantId,
  });
}

export function useWeeklyActivity() {
  const { tenantId } = useAuth();

  return useQuery({
    queryKey: ["metricas", "weekly-activity", { tenantId }],
    queryFn: () => api.get<WeeklyActivityPoint[]>("/metricas/weekly-activity"),
    enabled: !!tenantId,
  });
}
