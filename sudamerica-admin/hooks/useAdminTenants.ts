"use client";

import { api } from "@/lib/api";
import type { PaginatedResponse, TenantAdmin } from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

interface TenantFilters {
	page?: number;
	page_size?: number;
	search?: string;
	plan?: string;
}

export function useTenants(filters: TenantFilters = {}) {
	const { page = 1, page_size = 20, search, plan } = filters;
	const params = new URLSearchParams();
	params.set("page", String(page));
	params.set("page_size", String(page_size));
	if (search) params.set("search", search);
	if (plan) params.set("plan", plan);

	return useQuery({
		queryKey: ["admin", "tenants", filters],
		queryFn: () => api.get<PaginatedResponse<TenantAdmin>>(`/tenants?${params.toString()}`),
	});
}

export function useTenant(id: string) {
	return useQuery({
		queryKey: ["admin", "tenant", id],
		queryFn: () => api.get<TenantAdmin>(`/tenants/${id}`),
		enabled: !!id,
	});
}

export function useUpdateTenant() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, data }: { id: string; data: Partial<TenantAdmin> }) =>
			api.patch<TenantAdmin>(`/tenants/${id}`, data),
		onSuccess: (_, variables) => {
			void qc.invalidateQueries({ queryKey: ["admin", "tenants"] });
			void qc.invalidateQueries({ queryKey: ["admin", "tenant", variables.id] });
			notifications.show({ color: "green", title: "Tenant actualizado", message: "" });
		},
		onError: (err: Error) => {
			notifications.show({ color: "red", title: "Error", message: err.message });
		},
	});
}

export function useDeactivateTenant() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (id: string) => api.delete(`/tenants/${id}`),
		onSuccess: (_, id) => {
			void qc.invalidateQueries({ queryKey: ["admin", "tenants"] });
			void qc.invalidateQueries({ queryKey: ["admin", "tenant", id] });
			notifications.show({ color: "yellow", title: "Tenant desactivado", message: "" });
		},
		onError: (err: Error) => {
			notifications.show({ color: "red", title: "Error", message: err.message });
		},
	});
}
