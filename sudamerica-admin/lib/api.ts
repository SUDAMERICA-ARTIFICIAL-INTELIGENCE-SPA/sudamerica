import type { AuthTokens } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_PATH = "/api/v1/admin";
const AUTH_PATH = "/api/v1/core";
const TIMEOUT_MS = 15_000;

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("admin_access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("admin_refresh_token");
}

function storeTokens(access: string, refresh: string): void {
  localStorage.setItem("admin_access_token", access);
  localStorage.setItem("admin_refresh_token", refresh);
}

export function clearTokens(): void {
  localStorage.removeItem("admin_access_token");
  localStorage.removeItem("admin_refresh_token");
}

let _refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  // Deduplicate: if a refresh is already in flight, reuse it
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return null;

    try {
      const res = await fetch(`${API_BASE}${AUTH_PATH}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });

      if (!res.ok) {
        clearTokens();
        return null;
      }

      const data = (await res.json()) as AuthTokens;
      storeTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      clearTokens();
      return null;
    }
  })();

  try {
    return await _refreshPromise;
  } finally {
    _refreshPromise = null;
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
  body?: unknown;
  skipAuth?: boolean;
  useAuthPath?: boolean;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { body, skipAuth = false, useAuthPath = false, ...init } = options;
  const basePath = useAuthPath ? AUTH_PATH : ADMIN_PATH;
  const url = `${API_BASE}${basePath}${path}`;

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
    const bodyInit = body !== undefined ? JSON.stringify(body) : null;

    let res = await fetch(url, {
      ...init,
      headers,
      ...(bodyInit !== null ? { body: bodyInit } : {}),
      signal: controller.signal,
    });

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
        throw new ApiError(401, "Sesión expirada");
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
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  get: <T>(path: string, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),

  patch: <T>(path: string, body?: unknown, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: Omit<FetchOptions, "body">) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
} as const;
