"use client";

import { api } from "@/lib/api";
import type { DataModelResponse } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function useDataModel() {
	return useQuery({
		queryKey: ["admin", "system", "data-model"],
		queryFn: () => api.get<DataModelResponse>("/system/data-model"),
		staleTime: 5 * 60_000,
	});
}
