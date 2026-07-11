"use client";

import { useAuth } from "@/lib/auth";
import { notifications } from "@mantine/notifications";
import { useMutation } from "@tanstack/react-query";

interface MediaUploadResponse {
  success: boolean;
  media_url: string;
  media_type: "image" | "document" | "video" | "audio";
  file_name: string | null;
  mimetype: string;
}

const MAX_FILE_SIZE_MB = 16;

const ALLOWED_TYPES: Record<string, "image" | "document" | "video" | "audio"> = {
  "image/jpeg": "image",
  "image/png": "image",
  "image/gif": "image",
  "image/webp": "image",
  "application/pdf": "document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
  "video/mp4": "video",
  "audio/ogg": "audio",
  "audio/mpeg": "audio",
  "audio/mp4": "audio",
};

function getServiceBase(): string {
  const envOrigin = process.env.NEXT_PUBLIC_API_CANALES?.trim();
  if (envOrigin && envOrigin !== "undefined" && envOrigin !== "null") {
    return `${envOrigin.replace(/\/+$/, "")}/api/v1/canales`;
  }
  if (typeof window !== "undefined") {
    const { hostname, protocol } = window.location;
    if (hostname.startsWith("frontend-") && hostname.endsWith(".run.app")) {
      return `${protocol}//canales-service${hostname.slice("frontend".length)}/api/v1/canales`;
    }
  }
  return "http://localhost:8004/api/v1/canales";
}

export function useMediaUpload() {
  const { tenantId } = useAuth();

  return useMutation({
    mutationFn: async (file: File): Promise<MediaUploadResponse> => {
      if (!tenantId) {
        throw new Error("No tenant context");
      }

      const mediaType = ALLOWED_TYPES[file.type];
      if (!mediaType) {
        throw new Error(
          `Tipo de archivo no soportado: ${file.type}. Usa JPG, PNG, PDF, MP4, etc.`,
        );
      }

      const sizeMb = file.size / (1024 * 1024);
      if (sizeMb > MAX_FILE_SIZE_MB) {
        throw new Error(
          `El archivo excede el límite de ${MAX_FILE_SIZE_MB}MB (${sizeMb.toFixed(1)}MB)`,
        );
      }

      const formData = new FormData();
      formData.append("file", file);

      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const headers: Record<string, string> = {};
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await fetch(`${getServiceBase()}/media/upload`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as Record<string, unknown>;
        throw new Error(
          typeof error.detail === "string" ? error.detail : `Error al subir archivo: HTTP ${response.status}`,
        );
      }

      return response.json() as Promise<MediaUploadResponse>;
    },
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    onError: (err) => {
      notifications.show({
        title: "Error al subir archivo",
        message: err instanceof Error ? err.message : "No se pudo subir el archivo",
        color: "red",
      });
    },
  });
}

export function getMediaType(file: File): "image" | "document" | "video" | "audio" | null {
  return ALLOWED_TYPES[file.type] ?? null;
}

export const ACCEPTED_FILE_TYPES =
  ".jpg,.jpeg,.png,.gif,.webp,.pdf,.xlsx,.docx,.mp4,.ogg,.mp3,.m4a";
