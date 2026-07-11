"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ConversationMessage } from "@/hooks/useConversationMessages";
import { LeadCanal } from "@/lib/enums";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface ReplyPayload {
  lead_id: string;
  message?: string;
  media_url?: string;
  media_type?: "image" | "document" | "video" | "audio";
  file_name?: string;
  caption?: string;
  mimetype?: string;
}

interface ReplyResponse {
  success: boolean;
  message_id: string | null;
  lead_id: string;
}

interface PaginatedMessages {
  data: ConversationMessage[];
  meta: { total: number; page: number; page_size: number; total_pages: number };
}

const MAX_MESSAGE_LENGTH = 4096;

export function useSendProspectoMessage() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ReplyPayload) => {
      if (!tenantId) {
        return Promise.reject(new Error("No tenant context"));
      }
      const trimmed = payload.message?.trim();
      const hasMedia = !!payload.media_url;

      if (!trimmed && !hasMedia) {
        return Promise.reject(new Error("El mensaje o archivo es requerido"));
      }
      if (trimmed && trimmed.length > MAX_MESSAGE_LENGTH) {
        return Promise.reject(
          new Error(`El mensaje excede el límite de ${MAX_MESSAGE_LENGTH} caracteres`),
        );
      }

      const body: ReplyPayload = { lead_id: payload.lead_id };
      if (trimmed) body.message = trimmed;
      if (payload.media_url) body.media_url = payload.media_url;
      if (payload.media_type) body.media_type = payload.media_type;
      if (payload.file_name) body.file_name = payload.file_name;
      if (payload.caption) body.caption = payload.caption;
      if (payload.mimetype) body.mimetype = payload.mimetype;

      return api.post<ReplyResponse>(
        "/whatsapp/reply",
        body,
        { service: "canales" },
      );
    },
    onMutate: async (variables) => {
      // Page 1 always contains the newest messages; prefer it for optimistic UI.
      const allQueries = queryClient.getQueriesData<PaginatedMessages>({
        queryKey: ["conversation-messages", variables.lead_id],
      });

      let targetKey: readonly unknown[] | null = null;
      let targetData: PaginatedMessages | null = null;

      for (const [key, data] of allQueries) {
        if (data?.data) {
          const page = data.meta?.page ?? 0;
          if (!targetData || page < (targetData.meta?.page ?? Number.MAX_SAFE_INTEGER)) {
            targetKey = key;
            targetData = data;
          }
        }
      }

      if (targetKey && targetData) {
        await queryClient.cancelQueries({ queryKey: targetKey });

        const content = variables.message?.trim()
          || variables.caption
          || `[${(variables.media_type ?? "archivo").toUpperCase()}]`;

        const optimisticMessage: ConversationMessage = {
          id: `optimistic-${Date.now()}`,
          role: "user",
          content,
          canal: LeadCanal.WHATSAPP,
          tokens_used: null,
          modelo: null,
          session_id: null,
          media_url: variables.media_url ?? null,
          media_type: variables.media_type ?? null,
          created_at: new Date().toISOString(),
        };

        queryClient.setQueryData<PaginatedMessages>(targetKey, {
          ...targetData,
          meta: {
            ...targetData.meta,
            total: targetData.meta.total + 1,
          },
          data: [...targetData.data, optimisticMessage],
        });

        return { previous: targetData, queryKey: targetKey };
      }

      return { previous: null, queryKey: null };
    },
    onError: (err, _variables, context) => {
      if (context?.previous && context.queryKey) {
        queryClient.setQueryData(context.queryKey, context.previous);
      }
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "No se pudo enviar el mensaje",
        color: "red",
      });
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["conversation-messages", variables.lead_id],
      });
      queryClient.invalidateQueries({
        queryKey: ["conversation-threads"],
      });
    },
  });
}
