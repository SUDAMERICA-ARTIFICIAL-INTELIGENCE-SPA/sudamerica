"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import type {
  MenuImportConfirmResult,
  MenuImportPreview,
  MenuImportPreviewItem,
} from "@/lib/types";

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

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Phase 1: Upload file, extract items via AI, return preview for review. */
export function useMenuImportPreview() {
  return useMutation<MenuImportPreview, ApiError, File>({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${getBaseUrl()}/menu/import/preview`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      });

      if (!res.ok) {
        let detail: unknown;
        try {
          detail = await res.json();
        } catch {
          detail = await res.text();
        }
        const message =
          typeof detail === "object" && detail !== null && "detail" in detail
            ? String((detail as Record<string, unknown>).detail)
            : `HTTP ${res.status}`;
        throw new ApiError(res.status, message, detail);
      }

      return res.json() as Promise<MenuImportPreview>;
    },
  });
}

/** Phase 2: Confirm reviewed items — bulk-create productos/categorias. */
export function useMenuImportConfirm() {
  const queryClient = useQueryClient();

  return useMutation<
    MenuImportConfirmResult,
    ApiError,
    {
      import_id: string;
      items: MenuImportPreviewItem[];
      set_as_official_pdf: boolean;
    }
  >({
    mutationFn: async (body) => {
      const res = await fetch(`${getBaseUrl()}/menu/import/confirm`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        let detail: unknown;
        try {
          detail = await res.json();
        } catch {
          detail = await res.text();
        }
        const message =
          typeof detail === "object" && detail !== null && "detail" in detail
            ? String((detail as Record<string, unknown>).detail)
            : `HTTP ${res.status}`;
        throw new ApiError(res.status, message, detail);
      }

      return res.json() as Promise<MenuImportConfirmResult>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["productos"] });
      queryClient.invalidateQueries({ queryKey: ["categorias"] });
    },
  });
}
