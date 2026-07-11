"use client";

import { api } from "@/lib/api";
import type {
	PaginatedResponse,
	ResetPasswordResponse,
	SetPasswordRequest,
	UserAdmin,
} from "@/lib/types";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

interface UserFilters {
	page?: number;
	page_size?: number;
	search?: string;
	role?: string;
	tenant_id?: string;
}

interface UseUsersOptions {
	enabled?: boolean;
}

export function useUsers(filters: UserFilters = {}, options: UseUsersOptions = {}) {
	const { page = 1, page_size = 20, search, role, tenant_id } = filters;
	const { enabled = true } = options;
	const params = new URLSearchParams();
	params.set("page", String(page));
	params.set("page_size", String(page_size));
	if (search) params.set("search", search);
	if (role) params.set("role", role);
	if (tenant_id) params.set("tenant_id", tenant_id);

	return useQuery({
		queryKey: ["admin", "users", filters],
		queryFn: () => api.get<PaginatedResponse<UserAdmin>>(`/users?${params.toString()}`),
		enabled,
	});
}

export function useUpdateUser() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, data }: { id: string; data: Partial<UserAdmin> }) =>
			api.patch<UserAdmin>(`/users/${id}`, data),
		onSuccess: () => {
			void qc.invalidateQueries({ queryKey: ["admin", "users"] });
			notifications.show({ color: "green", title: "Usuario actualizado", message: "" });
		},
		onError: (err: Error) => {
			notifications.show({ color: "red", title: "Error", message: err.message });
		},
	});
}

export function useResetPassword() {
	return useMutation({
		mutationFn: (id: string) =>
			api.post<ResetPasswordResponse>(`/users/${id}/reset-password`),
		onSuccess: (data) => {
			notifications.show({
				color: "green",
				title: "Contraseña reseteada",
				message: `Nueva contraseña temporal: ${data.temp_password}`,
				autoClose: false,
			});
		},
		onError: (err: Error) => {
			notifications.show({ color: "red", title: "Error", message: err.message });
		},
	});
}

export function useSetPassword() {
	return useMutation({
		mutationFn: (body: SetPasswordRequest) =>
			api.post<{ status: string }>("/users/set-password", body),
		onSuccess: () => {
			notifications.show({
				color: "green",
				title: "Contraseña actualizada",
				message: "La nueva contraseña fue establecida correctamente.",
			});
		},
		onError: (err: Error) => {
			notifications.show({ color: "red", title: "Error", message: err.message });
		},
	});
}
