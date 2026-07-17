import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth";

// Mock next/navigation
const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

// Mock api module
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
vi.mock("@/lib/api", () => ({
  AUTH_TOKENS_UPDATED_EVENT: "auth:tokens-updated",
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.name = "ApiError";
    }
  },
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    patch: vi.fn(),
  },
}));

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete store[key];
  }),
};
vi.stubGlobal("localStorage", localStorageMock);
vi.stubGlobal("dispatchEvent", vi.fn());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    );
  };
}

// Helper to create a fake JWT payload
function fakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.fake-signature`;
}

beforeEach(() => {
  vi.clearAllMocks();
  for (const key of Object.keys(store)) delete store[key];
  mockPush.mockClear();
  mockReplace.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useAuth - initial state", () => {
  it("starts unauthenticated when no tokens in storage", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.tenantId).toBeNull();
  });

  it("hydrates from localStorage when valid tokens exist", async () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const token = fakeJwt({
      sub: "user-1",
      tenant_id: "tenant-1",
      role: "ADMIN",
      exp: futureExp,
      iat: 0,
    });
    store.access_token = token;
    store.refresh_token = "refresh-123";

    const mockUser = {
      id: "user-1",
      tenant_id: "tenant-1",
      nombre: "Test",
      email: "test@test.com",
      role: "ADMIN",
      activo: true,
      created_at: "2026-01-01",
    };
    mockApiGet.mockResolvedValueOnce(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.tenantId).toBe("tenant-1");
  });

  it("clears expired tokens from storage", async () => {
    const pastExp = Math.floor(Date.now() / 1000) - 3600;
    const token = fakeJwt({
      sub: "user-1",
      tenant_id: "tenant-1",
      role: "ADMIN",
      exp: pastExp,
      iat: 0,
    });
    store.access_token = token;
    store.refresh_token = "refresh-123";

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
  });

  it("clears tokens when /auth/me fails", async () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const token = fakeJwt({
      sub: "user-1",
      tenant_id: "tenant-1",
      role: "ADMIN",
      exp: futureExp,
      iat: 0,
    });
    store.access_token = token;
    store.refresh_token = "refresh-123";

    mockApiGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
  });
});

describe("useAuth - login", () => {
  it("stores tokens and fetches user on login", async () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const accessToken = fakeJwt({
      sub: "user-1",
      tenant_id: "tenant-1",
      role: "ADMIN",
      exp: futureExp,
      iat: 0,
    });

    mockApiPost.mockResolvedValueOnce({
      access_token: accessToken,
      refresh_token: "refresh-new",
    });

    const mockUser = {
      id: "user-1",
      tenant_id: "tenant-1",
      nombre: "Test",
      email: "test@test.com",
      role: "ADMIN",
      activo: true,
      created_at: "2026-01-01",
    };
    mockApiGet.mockResolvedValueOnce(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.login({ email: "test@test.com", password: "pass123" });
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    expect(localStorageMock.setItem).toHaveBeenCalledWith("access_token", accessToken);
    expect(localStorageMock.setItem).toHaveBeenCalledWith("refresh_token", "refresh-new");
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });
});

describe("useAuth - logout", () => {
  it("clears tokens and redirects to /acceso", async () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const token = fakeJwt({
      sub: "user-1",
      tenant_id: "tenant-1",
      role: "ADMIN",
      exp: futureExp,
      iat: 0,
    });
    store.access_token = token;
    store.refresh_token = "refresh-123";

    mockApiGet.mockResolvedValueOnce({
      id: "user-1",
      tenant_id: "tenant-1",
      nombre: "Test",
      email: "test@test.com",
      role: "ADMIN",
      activo: true,
      created_at: "2026-01-01",
    });

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
    expect(mockPush).toHaveBeenCalledWith("/acceso");
  });
});

describe("useAuth - parseJwt edge cases", () => {
  it("handles malformed JWT gracefully (no second segment)", async () => {
    store.access_token = "not-a-jwt";
    store.refresh_token = "refresh";

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
  });

  it("handles JWT with missing required fields", async () => {
    const token = fakeJwt({ foo: "bar" }); // missing sub, tenant_id
    store.access_token = token;
    store.refresh_token = "refresh";

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
  });
});

describe("useAuth - throws outside provider", () => {
  it("throws when used outside AuthProvider", () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    expect(() => {
      renderHook(() => useAuth(), { wrapper });
    }).toThrow("useAuth must be used within AuthProvider");
  });
});
