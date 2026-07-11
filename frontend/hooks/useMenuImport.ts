import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";

const SERVICE_CONFIG = {
  envOrigin: process.env.NEXT_PUBLIC_API_EXECUTE,
  cloudRunService: "api-execute",
  localOrigin: "http://localhost:8000",
  path: "/api/v1/core",
} as const;

function getBaseUrl(): string {
  const explicit = SERVICE_CONFIG.envOrigin?.trim();
  if (explicit && explicit !== "undefined" && explicit !== "null") {
    return `${explicit.replace(/\/+$/, "")}${SERVICE_CONFIG.path}`;
  }
  if (typeof window !== "undefined") {
    const { hostname, protocol } = window.location;
    if (hostname.startsWith("frontend-") && hostname.endsWith(".run.app")) {
      const origin = `${protocol}//${SERVICE_CONFIG.cloudRunService}${hostname.slice("frontend".length)}`;
      return `${origin}${SERVICE_CONFIG.path}`;
    }
  }
  return `${SERVICE_CONFIG.localOrigin}${SERVICE_CONFIG.path}`;
}

export interface MenuImportResult {
  created: number;
  categories_created: number;
  errors: string[];
  raw_response?: string;
}

export function useMenuImport() {
  const queryClient = useQueryClient();

  return useMutation<MenuImportResult, ApiError, File>({
    mutationFn: async (file: File) => {
      const token = typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${getBaseUrl()}/menu/import`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        let detail: unknown;
        try { detail = await res.json(); } catch { detail = await res.text(); }
        const message = typeof detail === "object" && detail !== null && "detail" in detail
          ? String((detail as Record<string, unknown>).detail)
          : `HTTP ${res.status}`;
        throw new ApiError(res.status, message, detail);
      }

      return res.json() as Promise<MenuImportResult>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["productos"] });
      queryClient.invalidateQueries({ queryKey: ["categorias"] });
    },
  });
}
