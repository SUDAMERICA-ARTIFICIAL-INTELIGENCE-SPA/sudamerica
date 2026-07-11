import { getDemoRubro, isDemoActive } from "@/lib/demo/state";
import type { ApiResponse, PaginatedResponse } from "@/lib/types";

type Service = keyof typeof SERVICE_CONFIG;

/**
 * Single gateway URL (Load Balancer / nginx) that routes by path prefix.
 * When set, all services are reached through this one origin.
 * Falls back to per-service URLs for backward compatibility.
 */
const API_GATEWAY = normalizePublicOrigin(process.env.NEXT_PUBLIC_API_GATEWAY);

const SERVICE_CONFIG = {
  execute: {
    envOrigin: process.env.NEXT_PUBLIC_API_EXECUTE,
    cloudRunService: "api-execute",
    localOrigin: "http://localhost:8000",
    path: "/api/v1/core",
  },
  dialer: {
    envOrigin: process.env.NEXT_PUBLIC_API_DIALER,
    cloudRunService: "ai-dialer",
    localOrigin: "http://localhost:8001",
    path: "/api/v1/ai",
  },
  callback: {
    envOrigin: process.env.NEXT_PUBLIC_API_CALLBACK,
    cloudRunService: "callback-manual",
    localOrigin: "http://localhost:8002",
    path: "/api/v1/reviews",
  },
  canales: {
    envOrigin: process.env.NEXT_PUBLIC_API_CANALES,
    cloudRunService: "canales-service",
    localOrigin: "http://localhost:8004",
    path: "/api/v1/canales",
  },
  tasks: {
    envOrigin: process.env.NEXT_PUBLIC_API_TASKS,
    cloudRunService: "tasks",
    localOrigin: "http://localhost:8003",
    path: "/api/v1/tasks",
  },
} as const;

const TIMEOUT_MS = 15_000;
export const AUTH_TOKENS_UPDATED_EVENT = "auth:tokens-updated";

/** Public base URL for api-execute (no /api/v1/core path). Used for public QR endpoints. */
export function getApiExecuteOrigin(): string {
  if (API_GATEWAY) return API_GATEWAY;
  const config = SERVICE_CONFIG.execute;
  const explicitOrigin = normalizePublicOrigin(config.envOrigin);
  const inferredOrigin = inferCloudRunOrigin(config.cloudRunService);
  return explicitOrigin ?? inferredOrigin ?? config.localOrigin;
}

/** Build the public QR scan URL for a mesa. */
export function getMesaQrUrl(qrToken: string): string {
  return `${getApiExecuteOrigin()}/api/v1/public/mesas/qr/${qrToken}`;
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function normalizePublicOrigin(value: string | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized || normalized === "undefined" || normalized === "null") {
    return null;
  }
  return stripTrailingSlash(normalized);
}

function inferCloudRunOrigin(serviceName: string): string | null {
  if (typeof window === "undefined") return null;

  const { hostname, protocol } = window.location;
  if (!hostname.startsWith("frontend-") || !hostname.endsWith(".run.app")) {
    return null;
  }

  return `${protocol}//${serviceName}${hostname.slice("frontend".length)}`;
}

function getServiceBase(service: Service): string {
  const config = SERVICE_CONFIG[service];
  if (API_GATEWAY) return `${API_GATEWAY}${config.path}`;
  const explicitOrigin = normalizePublicOrigin(config.envOrigin);
  const inferredOrigin = inferCloudRunOrigin(config.cloudRunService);
  const origin = explicitOrigin ?? inferredOrigin ?? config.localOrigin;
  return `${origin}${config.path}`;
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function storeTokens(access: string, refresh: string): void {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
  window.dispatchEvent(new CustomEvent(AUTH_TOKENS_UPDATED_EVENT));
}

function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.dispatchEvent(new CustomEvent(AUTH_TOKENS_UPDATED_EVENT));
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  try {
    const res = await fetch(`${getServiceBase("execute")}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!res.ok) {
      clearTokens();
      return null;
    }

    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    storeTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  service?: Service;
  body?: unknown;
  skipAuth?: boolean;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { service = "execute", body, skipAuth = false, ...init } = options;
  const url = `${getServiceBase(service)}${path}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  try {
    const bodyInit =
      body !== undefined ? JSON.stringify(body) : init.method !== "GET" ? "{}" : null;

    let res = await fetch(url, {
      ...init,
      headers,
      ...(bodyInit !== null ? { body: bodyInit } : {}),
      signal: controller.signal,
    });

    // Token refresh on 401
    if (res.status === 401 && !skipAuth) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        headers.Authorization = `Bearer ${newToken}`;
        res = await fetch(url, {
          ...init,
          headers,
          ...(bodyInit !== null ? { body: bodyInit } : {}),
        });
      } else {
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        throw new ApiError(401, "Session expired");
      }
    }

    if (!res.ok) {
      let errorDetail: unknown;
      try {
        errorDetail = await res.json();
      } catch {
        errorDetail = await res.text();
      }
      const message =
        typeof errorDetail === "object" &&
        errorDetail !== null &&
        "detail" in errorDetail &&
        typeof (errorDetail as Record<string, unknown>).detail === "string"
          ? String((errorDetail as Record<string, unknown>).detail)
          : `HTTP ${res.status}`;
      throw new ApiError(res.status, message, errorDetail);
    }

    return res.json() as Promise<T>;
  } catch (err) {
    // Network errors (browser reports as "CORS" when server returns error without body)
    // or AbortController timeout — attempt token refresh as it may be an auth issue
    if (err instanceof TypeError && !skipAuth) {
      const newToken = await refreshAccessToken();
      if (!newToken && typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  get: <T>(path: string, options?: Omit<FetchOptions, "body">) => {
    // Showroom DEMO: sin backend → el resolver (code-split) sirve fixtures del
    // rubro activo. Fuera del route group `(showroom)` isDemoActive() es false y
    // este branch nunca se toma → la app real hace fetch normal.
    if (isDemoActive()) {
      return import("@/lib/demo/resolver").then((m) => m.demoResolve<T>(path, getDemoRubro()));
    }
    return apiFetch<T>(path, { ...options, method: "GET" });
  },

  post: <T>(path: string, body?: unknown, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),

  patch: <T>(path: string, body?: unknown, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),

  put: <T>(path: string, body?: unknown, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),

  delete: <T>(path: string, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
} as const;

/** Resolved gateway origin (https://...) or null if not configured. */
export function getGatewayOrigin(): string | null {
  return API_GATEWAY;
}

// Re-export envelope types for consumer convenience
export type { ApiResponse, PaginatedResponse };
