"use client";

import { api } from "@/lib/api";
import type { MetricsOverview, TimeseriesPoint, TopTenantItem } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function useMetricsOverview() {
  return useQuery({
    queryKey: ["admin", "metrics", "overview"],
    queryFn: () => api.get<MetricsOverview>("/metrics/overview"),
    refetchInterval: 60_000,
  });
}

export function useMetricsTimeseries(days = 30) {
  return useQuery({
    queryKey: ["admin", "metrics", "timeseries", days],
    queryFn: () => api.get<TimeseriesPoint[]>(`/metrics/timeseries?days=${days}`),
  });
}

export function useTopTenants(limit = 10) {
  return useQuery({
    queryKey: ["admin", "metrics", "top-tenants", limit],
    queryFn: () => api.get<TopTenantItem[]>(`/metrics/top-tenants?limit=${limit}`),
  });
}
