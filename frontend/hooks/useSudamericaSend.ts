import type { SudamericaMessage } from "@/hooks/useSudamericaChat";
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface SudamericaChatResponse {
  response: string;
  tokens_used: number;
  model_used: string;
  tools_used: Array<{ name: string; result_summary: string }>;
}

interface SudamericaHistoryCache {
  data: SudamericaMessage[];
  total: number;
  page: number;
  page_size: number;
}

interface SudamericaSendInput {
  message: string;
  file?: File | null;
}

function getServiceBase(): string {
  if (typeof window === "undefined") return "http://localhost:8000/api/v1/core";
  const { hostname, protocol } = window.location;
  if (hostname.startsWith("frontend-") && hostname.endsWith(".run.app")) {
    const suffix = hostname.slice("frontend".length);
    return `${protocol}//api-execute${suffix}/api/v1/core`;
  }
  return (
    process.env.NEXT_PUBLIC_API_EXECUTE?.replace(/\/+$/, "") ||
    "http://localhost:8000"
  ) + "/api/v1/core";
}

export function useSudamericaSend() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ message, file }: SudamericaSendInput) => {
      const formData = new FormData();
      formData.append("message", message);
      if (file) {
        formData.append("file", file);
      }

      const token = localStorage.getItem("access_token");
      const base = getServiceBase();

      const res = await fetch(`${base}/sudamerica/chat`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }

      return (await res.json()) as SudamericaChatResponse;
    },
    onMutate: async ({ message, file }) => {
      await queryClient.cancelQueries({ queryKey: ["sudamerica", "history"] });
      const previous = queryClient.getQueryData(["sudamerica", "history"]);

      const displayText = file
        ? `${message}\n📎 ${file.name}`
        : message;

      queryClient.setQueryData(
        ["sudamerica", "history"],
        (old: SudamericaHistoryCache | undefined) => {
          const optimisticMsg: SudamericaMessage = {
            id: `optimistic-${Date.now()}`,
            role: "user",
            content: displayText,
            tokens_used: null,
            modelo: null,
            created_at: new Date().toISOString(),
          };
          return {
            data: [...(old?.data ?? []), optimisticMsg],
            total: (old?.total ?? 0) + 1,
            page: old?.page ?? 1,
            page_size: old?.page_size ?? 100,
          };
        },
      );

      return { previous };
    },
    onSuccess: (data) => {
      queryClient.setQueryData(
        ["sudamerica", "history"],
        (old: SudamericaHistoryCache | undefined) => {
          const assistantMsg: SudamericaMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: data.response,
            tokens_used: data.tokens_used,
            modelo: data.model_used,
            created_at: new Date().toISOString(),
          };
          return {
            data: [...(old?.data ?? []), assistantMsg],
            total: (old?.total ?? 0) + 1,
            page: old?.page ?? 1,
            page_size: old?.page_size ?? 100,
          };
        },
      );
    },
    onError: (_err, _input, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["sudamerica", "history"], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sudamerica", "history"] });
    },
  });
}
