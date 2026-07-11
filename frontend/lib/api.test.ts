import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_TOKENS_UPDATED_EVENT, ApiError, api } from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Typecheck-safe access to the first recorded fetch call (calls[0] may be undefined).
function firstFetchCall() {
  const call = mockFetch.mock.calls[0];
  if (!call) throw new Error("fetch was not called");
  return call;
}

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: () => {
      store = {};
    },
  };
})();
vi.stubGlobal("localStorage", localStorageMock);

// Mock window.location
const locationMock = { hostname: "localhost", protocol: "http:", href: "" };
vi.stubGlobal("location", locationMock);

// Mock window.dispatchEvent
vi.stubGlobal("dispatchEvent", vi.fn());

// Mock AbortController
vi.stubGlobal(
  "AbortController",
  class {
    signal = {};
    abort = vi.fn();
  },
);

beforeEach(() => {
  vi.useFakeTimers();
  localStorageMock.clear();
  mockFetch.mockReset();
  locationMock.hostname = "localhost";
  locationMock.protocol = "http:";
  locationMock.href = "";
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ApiError", () => {
  it("creates an error with status and message", () => {
    const error = new ApiError(404, "Not Found");
    expect(error.status).toBe(404);
    expect(error.message).toBe("Not Found");
    expect(error.name).toBe("ApiError");
    expect(error.detail).toBeUndefined();
  });

  it("includes detail when provided", () => {
    const detail = { field: "email", reason: "invalid" };
    const error = new ApiError(422, "Validation Error", detail);
    expect(error.detail).toEqual(detail);
  });

  it("is an instance of Error", () => {
    const error = new ApiError(500, "Server Error");
    expect(error).toBeInstanceOf(Error);
  });
});

describe("AUTH_TOKENS_UPDATED_EVENT", () => {
  it("is a string constant", () => {
    expect(typeof AUTH_TOKENS_UPDATED_EVENT).toBe("string");
    expect(AUTH_TOKENS_UPDATED_EVENT).toBe("auth:tokens-updated");
  });
});

describe("api.get", () => {
  it("sends GET request with auth header when token is stored", async () => {
    localStorageMock.setItem("access_token", "test-token-123");

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: [1, 2, 3] }),
    });

    const result = await api.get<{ data: number[] }>("/leads");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = firstFetchCall();
    expect(url).toContain("/leads");
    expect(options.headers.Authorization).toBe("Bearer test-token-123");
    expect(options.method).toBe("GET");
    expect(result).toEqual({ data: [1, 2, 3] });
  });

  it("sends GET request without auth header when skipAuth is true", async () => {
    localStorageMock.setItem("access_token", "test-token-123");

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ ok: true }),
    });

    await api.get("/health", { skipAuth: true });

    const [, options] = firstFetchCall();
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("sends GET without auth header when no token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/leads");

    const [, options] = firstFetchCall();
    expect(options.headers.Authorization).toBeUndefined();
  });
});

describe("api.post", () => {
  it("sends POST with JSON body", async () => {
    localStorageMock.setItem("access_token", "test-token");

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: "new-lead" }),
    });

    const result = await api.post("/leads", { nombre: "Test Lead" });

    const [, options] = firstFetchCall();
    expect(options.body).toBe(JSON.stringify({ nombre: "Test Lead" }));
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(result).toEqual({ id: "new-lead" });
  });

  it("sends empty body {} when no body provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ ok: true }),
    });

    await api.post("/action");

    const [, options] = firstFetchCall();
    expect(options.body).toBe("{}");
  });
});

describe("api.patch", () => {
  it("sends PATCH with JSON body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: "1", nombre: "Updated" }),
    });

    await api.patch("/leads/1", { nombre: "Updated" });

    const [, options] = firstFetchCall();
    expect(options.method).toBe("PATCH");
    expect(options.body).toBe(JSON.stringify({ nombre: "Updated" }));
  });
});

describe("api.delete", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true }),
    });

    await api.delete("/leads/1");

    const [, options] = firstFetchCall();
    expect(options.method).toBe("DELETE");
  });
});

describe("error handling", () => {
  it("throws ApiError with detail from JSON response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: "Email already exists" }),
    });

    await expect(api.get("/leads")).rejects.toThrow(ApiError);

    try {
      await api.get("/leads");
    } catch {
      // Already tested above
    }
  });

  it("throws ApiError with HTTP status when no detail", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
      text: () => Promise.resolve("Internal Server Error"),
    });

    await expect(api.get("/leads")).rejects.toThrow("HTTP 500");
  });

  it("attempts token refresh on 401", async () => {
    localStorageMock.setItem("access_token", "expired-token");
    localStorageMock.setItem("refresh_token", "valid-refresh");

    // First call returns 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Token expired" }),
    });

    // Refresh call succeeds
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
        }),
    });

    // Retry call succeeds
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: "success" }),
    });

    const result = await api.get<{ data: string }>("/protected");

    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(result).toEqual({ data: "success" });
    expect(localStorageMock.setItem).toHaveBeenCalledWith("access_token", "new-access-token");
    expect(localStorageMock.setItem).toHaveBeenCalledWith("refresh_token", "new-refresh-token");
  });

  it("redirects to /login when refresh fails", async () => {
    localStorageMock.setItem("access_token", "expired-token");
    localStorageMock.setItem("refresh_token", "invalid-refresh");

    // First call returns 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Token expired" }),
    });

    // Refresh call fails
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid refresh" }),
    });

    await expect(api.get("/protected")).rejects.toThrow("Session expired");
    expect(locationMock.href).toBe("/login");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
  });
});

describe("service routing", () => {
  it("routes to dialer service", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/config", { service: "dialer" });

    const [url] = firstFetchCall();
    expect(url).toContain("localhost:8001");
    expect(url).toContain("/api/v1/ai/config");
  });

  it("routes to canales service", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/qr/test", { service: "canales" });

    const [url] = firstFetchCall();
    expect(url).toContain("localhost:8004");
    expect(url).toContain("/api/v1/canales/qr/test");
  });

  it("routes to tasks service", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/status", { service: "tasks" });

    const [url] = firstFetchCall();
    expect(url).toContain("localhost:8003");
    expect(url).toContain("/api/v1/tasks/status");
  });

  it("defaults to execute service", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/leads");

    const [url] = firstFetchCall();
    expect(url).toContain("localhost:8000");
    expect(url).toContain("/api/v1/core/leads");
  });

  it("infers Cloud Run origin from frontend hostname", async () => {
    locationMock.hostname = "frontend-12345.us-central1.run.app";
    locationMock.protocol = "https:";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/leads");

    const [url] = firstFetchCall();
    expect(url).toContain("api-execute-12345.us-central1.run.app");
  });
});
