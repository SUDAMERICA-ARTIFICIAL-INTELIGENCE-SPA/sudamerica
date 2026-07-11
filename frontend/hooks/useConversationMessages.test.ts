import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useConversationMessages } from "./useConversationMessages";

// Mock auth
const mockTenantId = { current: "tenant-123" as string | null };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ tenantId: mockTenantId.current }),
}));

// Mock api
const mockApiGet = vi.fn();
vi.mock("@/lib/api", () => ({
  api: { get: (...args: unknown[]) => mockApiGet(...args) },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockTenantId.current = "tenant-123";
});

describe("useConversationMessages", () => {
  it("does not fetch when leadId is null", async () => {
    const { result } = renderHook(() => useConversationMessages(null), {
      wrapper: createWrapper(),
    });

    // Wait a tick and confirm no fetch was made
    await new Promise((r) => setTimeout(r, 50));
    expect(mockApiGet).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("does not fetch when leadId is not a valid UUID", async () => {
    const { result } = renderHook(() => useConversationMessages("not-a-uuid"), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockApiGet).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("does not fetch when tenantId is null", async () => {
    mockTenantId.current = null;
    const validUuid = "550e8400-e29b-41d4-a716-446655440000";

    renderHook(() => useConversationMessages(validUuid), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it("fetches when leadId is a valid UUID and tenantId exists", async () => {
    const validUuid = "550e8400-e29b-41d4-a716-446655440000";
    const mockResponse = {
      data: [{ id: "msg-1", role: "user", content: "Hola", created_at: "2026-01-01" }],
      meta: { total: 1, page: 1, page_size: 50, total_pages: 1 },
    };
    mockApiGet.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useConversationMessages(validUuid), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockResponse);
    });

    expect(mockApiGet).toHaveBeenCalledWith(
      `/conversations/${validUuid}/messages?page=1&page_size=50`,
      { service: "dialer" },
    );
  });

  it("passes page parameter correctly", async () => {
    const validUuid = "550e8400-e29b-41d4-a716-446655440000";
    mockApiGet.mockResolvedValueOnce({
      data: [],
      meta: { total: 0, page: 3, page_size: 50, total_pages: 0 },
    });

    renderHook(() => useConversationMessages(validUuid, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalled();
    });

    expect(mockApiGet).toHaveBeenCalledWith(
      `/conversations/${validUuid}/messages?page=3&page_size=50`,
      { service: "dialer" },
    );
  });

  it("validates various UUID formats", async () => {
    const validUuids = [
      "550e8400-e29b-41d4-a716-446655440000",
      "ABCDEF00-1234-5678-9ABC-DEF012345678",
      "00000000-0000-0000-0000-000000000000",
    ];

    for (const uuid of validUuids) {
      mockApiGet.mockResolvedValueOnce({
        data: [],
        meta: { total: 0, page: 1, page_size: 50, total_pages: 0 },
      });

      const { unmount } = renderHook(() => useConversationMessages(uuid), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockApiGet).toHaveBeenCalled();
      });

      unmount();
      mockApiGet.mockClear();
    }
  });

  it("rejects invalid UUID formats", async () => {
    const invalidIds = [
      "",
      "123",
      "not-uuid-format",
      "550e8400-e29b-41d4-a716",
      "550e8400-e29b-41d4-a716-44665544000Z", // non-hex char
    ];

    for (const id of invalidIds) {
      renderHook(() => useConversationMessages(id), {
        wrapper: createWrapper(),
      });
    }

    await new Promise((r) => setTimeout(r, 100));
    expect(mockApiGet).not.toHaveBeenCalled();
  });
});
