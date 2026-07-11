import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSendProspectoMessage } from "./useSendProspectoMessage";

// Mock auth
const mockTenantId = { current: "tenant-123" as string | null };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ tenantId: mockTenantId.current }),
}));

// Mock api
const mockApiPost = vi.fn();
vi.mock("@/lib/api", () => ({
  api: { post: (...args: unknown[]) => mockApiPost(...args) },
}));

// Mock notifications
const mockNotificationsShow = vi.fn();
vi.mock("@mantine/notifications", () => ({
  notifications: { show: (...args: unknown[]) => mockNotificationsShow(...args) },
}));

// Mock enums
vi.mock("@/lib/enums", () => ({
  LeadCanal: { WHATSAPP: "WHATSAPP" },
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

describe("useSendProspectoMessage", () => {
  it("rejects when tenantId is null", async () => {
    mockTenantId.current = null;

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "Hola" });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("No tenant context");
    expect(mockApiPost).not.toHaveBeenCalled();
  });

  it("rejects empty message without media", async () => {
    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "" });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("El mensaje o archivo es requerido");
  });

  it("rejects whitespace-only message without media", async () => {
    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "   \n\t  " });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("El mensaje o archivo es requerido");
  });

  it("rejects message exceeding 4096 characters", async () => {
    const longMessage = "a".repeat(4097);

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: longMessage });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toContain("4096");
  });

  it("sends valid text message successfully", async () => {
    mockApiPost.mockResolvedValueOnce({
      success: true,
      message_id: "msg-1",
      lead_id: "lead-1",
    });

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "Hola, buen dia!" });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockApiPost).toHaveBeenCalledWith(
      "/whatsapp/reply",
      { lead_id: "lead-1", message: "Hola, buen dia!" },
      { service: "canales" },
    );
  });

  it("trims message before sending", async () => {
    mockApiPost.mockResolvedValueOnce({
      success: true,
      message_id: "msg-1",
      lead_id: "lead-1",
    });

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "  Hola!  " });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const call = mockApiPost.mock.calls[0] as unknown[];
    expect((call[1] as Record<string, unknown>).message).toBe("Hola!");
  });

  it("allows media-only message without text", async () => {
    mockApiPost.mockResolvedValueOnce({
      success: true,
      message_id: "msg-1",
      lead_id: "lead-1",
    });

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        lead_id: "lead-1",
        media_url: "https://storage.example.com/image.jpg",
        media_type: "image",
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const call1 = mockApiPost.mock.calls[0] as unknown[];
    const body1 = call1[1] as Record<string, unknown>;
    expect(body1.media_url).toBe("https://storage.example.com/image.jpg");
    expect(body1.media_type).toBe("image");
    expect(body1.message).toBeUndefined();
  });

  it("includes all media fields in payload", async () => {
    mockApiPost.mockResolvedValueOnce({
      success: true,
      message_id: "msg-1",
      lead_id: "lead-1",
    });

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        lead_id: "lead-1",
        message: "Mira esto",
        media_url: "https://storage.example.com/doc.pdf",
        media_type: "document",
        file_name: "menu.pdf",
        caption: "Nuevo menu",
        mimetype: "application/pdf",
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const call2 = mockApiPost.mock.calls[0] as unknown[];
    expect(call2[1]).toEqual({
      lead_id: "lead-1",
      message: "Mira esto",
      media_url: "https://storage.example.com/doc.pdf",
      media_type: "document",
      file_name: "menu.pdf",
      caption: "Nuevo menu",
      mimetype: "application/pdf",
    });
  });

  it("shows error notification on failure", async () => {
    mockApiPost.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: "Hola" });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockNotificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Error",
        color: "red",
      }),
    );
  });

  it("accepts exactly 4096 characters", async () => {
    mockApiPost.mockResolvedValueOnce({
      success: true,
      message_id: "msg-1",
      lead_id: "lead-1",
    });

    const maxMessage = "a".repeat(4096);

    const { result } = renderHook(() => useSendProspectoMessage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ lead_id: "lead-1", message: maxMessage });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockApiPost).toHaveBeenCalled();
  });
});
