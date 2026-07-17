"use client";

import { AUTH_TOKENS_UPDATED_EVENT, ApiError, api } from "@/lib/api";
import type { AuthState, AuthTokens, JwtPayload, Usuario } from "@/lib/types";
import { useRouter } from "next/navigation";
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterCredentials {
  email: string;
  password: string;
  nombre: string;
  apellido: string;
  tenant_nombre: string;
  rubro?: string;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function parseJwt(token: string): JwtPayload | null {
  try {
    const base64 = token.split(".")[1];
    if (!base64) return null;
    const decoded = JSON.parse(atob(base64)) as unknown;
    if (
      typeof decoded === "object" &&
      decoded !== null &&
      "sub" in decoded &&
      "tenant_id" in decoded
    ) {
      return decoded as JwtPayload;
    }
    return null;
  } catch {
    return null;
  }
}

function loadStoredTokens(): AuthTokens | null {
  if (typeof window === "undefined") return null;
  const access = localStorage.getItem("access_token");
  const refresh = localStorage.getItem("refresh_token");
  if (!access || !refresh) return null;
  return { access_token: access, refresh_token: refresh };
}

function emitAuthTokenUpdate() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(AUTH_TOKENS_UPDATED_EVENT));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    tokens: null,
    tenantId: null,
    sucursalId: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Hydrate from localStorage on mount
  useEffect(() => {
    // ── DEV MOCK: bypass auth when backend is offline ──────────────────────
    if (process.env.NODE_ENV === "development" && process.env.NEXT_PUBLIC_MOCK_AUTH === "true") {
      setState({
        user: {
          id: "mock-user-1",
          tenant_id: "mock-tenant-1",
          nombre: "Demo User",
          email: "demo@sudamerica.ai",
          role: "ADMIN" as import("@/lib/enums").UserRole,
          sucursal_id: null,
          activo: true,
          created_at: new Date().toISOString(),
        } as import("@/lib/types").Usuario,
        tokens: { access_token: "mock", refresh_token: "mock" },
        tenantId: "mock-tenant-1",
        sucursalId: null,
      });
      setIsLoading(false);
      return;
    }
    // ──────────────────────────────────────────────────────────────────────

    const tokens = loadStoredTokens();
    if (!tokens) {
      setIsLoading(false);
      return;
    }

    const payload = parseJwt(tokens.access_token);
    if (!payload || payload.exp * 1000 < Date.now()) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      emitAuthTokenUpdate();
      setIsLoading(false);
      return;
    }

    api
      .get<Usuario>("/auth/me")
      .then((user) => {
        setState({
          user,
          tokens,
          tenantId: payload.tenant_id,
          sucursalId: payload.sucursal_id ?? null,
        });
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        emitAuthTokenUpdate();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const result = await api.post<AuthTokens>("/auth/login", credentials, {
        skipAuth: true,
      });

      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("refresh_token", result.refresh_token);
      emitAuthTokenUpdate();

      const payload = parseJwt(result.access_token);
      const user = await api.get<Usuario>("/auth/me");

      setState({
        user,
        tokens: result,
        tenantId: payload?.tenant_id ?? null,
        sucursalId: payload?.sucursal_id ?? null,
      });

      router.push("/dashboard");
    },
    [router],
  );

  const register = useCallback(
    async (credentials: RegisterCredentials) => {
      const result = await api.post<AuthTokens>("/auth/register", credentials, {
        skipAuth: true,
      });

      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("refresh_token", result.refresh_token);
      emitAuthTokenUpdate();

      const payload = parseJwt(result.access_token);
      const user = await api.get<Usuario>("/auth/me");

      setState({
        user,
        tokens: result,
        tenantId: payload?.tenant_id ?? null,
        sucursalId: payload?.sucursal_id ?? null,
      });

      // Restaurant config (carta, IA agent, WhatsApp) is collected in the
      // post-registration onboarding wizard.
      router.push("/registro");
    },
    [router],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    emitAuthTokenUpdate();
    setState({ user: null, tokens: null, tenantId: null, sucursalId: null });
    router.push("/acceso");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      register,
      logout,
      isAuthenticated: state.user !== null,
      isLoading,
    }),
    [state, login, register, logout, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/acceso");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) return null;
  return <>{children}</>;
}

// Export ApiError so callers can identify auth errors
export { ApiError };
