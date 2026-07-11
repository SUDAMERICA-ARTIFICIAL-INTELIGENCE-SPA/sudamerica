import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export interface SudamericaMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tokens_used: number | null;
  modelo: string | null;
  created_at: string;
}

interface SudamericaHistoryResponse {
  data: SudamericaMessage[];
  total: number;
  page: number;
  page_size: number;
}

export function useSudamericaChat() {
  return useQuery<SudamericaHistoryResponse>({
    queryKey: ["sudamerica", "history"],
    queryFn: () =>
      api.get<SudamericaHistoryResponse>("/sudamerica/history?page_size=100"),
    refetchInterval: false,
    staleTime: 0,
  });
}
