"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import { notifications } from "@mantine/notifications";
import type { Producto } from "@/lib/types";

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

export function useUploadProductImage() {
  const qc = useQueryClient();

  return useMutation<Producto, ApiError, { productoId: string; file: File }>({
    mutationFn: async ({ productoId, file }) => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("access_token")
          : null;

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(
        `${getBaseUrl()}/productos/${productoId}/imagen`,
        {
          method: "POST",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: formData,
        }
      );

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

      return res.json() as Promise<Producto>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["productos"] });
      notifications.show({
        color: "green",
        title: "Imagen subida",
        message: "La imagen del producto fue actualizada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error al subir imagen",
        message: err.message,
      });
    },
  });
}

export function useDeleteProductImage() {
  const qc = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: async (productoId: string) => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("access_token")
          : null;

      const res = await fetch(
        `${getBaseUrl()}/productos/${productoId}/imagen`,
        {
          method: "DELETE",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );

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
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["productos"] });
      notifications.show({
        color: "orange",
        title: "Imagen eliminada",
        message: "La imagen del producto fue eliminada.",
      });
    },
    onError: (err: Error) => {
      notifications.show({
        color: "red",
        title: "Error",
        message: err.message,
      });
    },
  });
}
