"use client";

import type { ConversationMessage } from "@/hooks/useConversationMessages";
import { useConversationMessages } from "@/hooks/useConversationMessages";
import { useSendProspectoMessage } from "@/hooks/useSendProspectoMessage";
import { useMediaUpload, ACCEPTED_FILE_TYPES, getMediaType } from "@/hooks/useMediaUpload";
import { OutboundComposer } from "@/components/prospectos/OutboundComposer";
import {
  ActionIcon,
  Badge,
  Box,
  CloseButton,
  Group,
  Image,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from "@mantine/core";
import {
  IconBrandWhatsapp,
  IconFile,
  IconFileText,
  IconMicrophone,
  IconPaperclip,
  IconPhoto,
  IconRobot,
  IconSend,
  IconUser,
  IconVideo,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface ConversationChatProps {
  leadId: string;
  leadName?: string;
}

// Strip null bytes and non-printable control chars (except \n \r \t) for display safety
const CONTROL_CHARS_RE = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;

// Strip AI system markers that should not be shown to users
// e.g. [ENVIAR_LISTA:...], [ENVIAR_POLL:...], [ENVIAR_MENU], [ENVIAR_IMAGEN:...], [ALERTA_MESERO], [PEDIR_CUENTA]
const AI_MARKER_RE =
  /\[ENVIAR_(?:LISTA|POLL|MENU(?:_PDF)?|IMAGEN):[^\]]*\]|\[(?:ALERTA_MESERO|PEDIR_CUENTA|ENVIAR_MENU(?:_PDF)?)\]/g;

function sanitizeContent(text: string): string {
  return text.replace(CONTROL_CHARS_RE, "").replace(AI_MARKER_RE, "").trim();
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("es-CL", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("es-CL", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function MediaPreview({ message }: { message: ConversationMessage }) {
  if (!message.media_url || !message.media_type) return null;

  const mediaType = message.media_type;

  if (mediaType === "image") {
    return (
      <Image
        src={message.media_url}
        alt="Imagen adjunta"
        radius="md"
        maw={280}
        mah={200}
        fit="contain"
        style={{ cursor: "pointer" }}
        onClick={() => window.open(message.media_url ?? "", "_blank")}
      />
    );
  }

  if (mediaType === "audio") {
    return (
      <Group gap="xs" py={4}>
        <IconMicrophone size={16} color="var(--mantine-color-blue-5)" />
        <audio controls preload="metadata" style={{ maxWidth: 240, height: 32 }}>
          <source src={message.media_url} />
        </audio>
      </Group>
    );
  }

  if (mediaType === "video") {
    return (
      <Group gap="xs" py={4}>
        <IconVideo size={16} color="var(--mantine-color-grape-5)" />
        <Text
          size="xs"
          c="blue"
          style={{ cursor: "pointer", textDecoration: "underline" }}
          onClick={() => window.open(message.media_url ?? "", "_blank")}
        >
          Ver video
        </Text>
      </Group>
    );
  }

  // document
  return (
    <Group
      gap="xs"
      py={4}
      style={{ cursor: "pointer" }}
      onClick={() => window.open(message.media_url ?? "", "_blank")}
    >
      <IconFileText size={16} color="var(--mantine-color-orange-5)" />
      <Text size="xs" c="blue" style={{ textDecoration: "underline" }}>
        Descargar documento
      </Text>
    </Group>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isAssistant = message.role === "assistant";

  return (
    <Box
      style={{
        display: "flex",
        justifyContent: isAssistant ? "flex-end" : "flex-start",
        paddingLeft: isAssistant ? 24 : 0,
        paddingRight: isAssistant ? 0 : 24,
      }}
    >
      <Paper
        p="sm"
        radius="lg"
        style={{
          backgroundColor: isAssistant
            ? "var(--mantine-color-indigo-light)"
            : "var(--mantine-color-default)",
          borderBottomRightRadius: isAssistant ? 4 : undefined,
          borderBottomLeftRadius: isAssistant ? undefined : 4,
          maxWidth: "88%",
          border: isAssistant
            ? undefined
            : "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group gap={4} mb={4}>
          {isAssistant ? (
            <IconRobot size={14} color="var(--mantine-color-indigo-light-color)" />
          ) : (
            <IconUser size={14} color="var(--mantine-color-orange-5)" />
          )}
          <Text size="xs" fw={600} c={isAssistant ? "indigo" : "orange.5"}>
            {isAssistant ? "IA" : "Prospecto"}
          </Text>
          {message.canal === "WHATSAPP" && <IconBrandWhatsapp size={12} color="#25D366" />}
        </Group>
        <MediaPreview message={message} />
        {message.content && !message.content.startsWith("[") && (
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
            {sanitizeContent(message.content)}
          </Text>
        )}
        <Group justify="flex-end" gap="xs" mt={4}>
          {isAssistant && message.tokens_used && (
            <Badge size="xs" variant="dot" color="gray">
              {message.tokens_used} tokens
            </Badge>
          )}
          <Text size="xs" c="dimmed">
            {formatTime(message.created_at)}
          </Text>
        </Group>
      </Paper>
    </Box>
  );
}

interface PendingFile {
  file: File;
  mediaType: "image" | "document" | "video" | "audio";
  preview: string | null;
}

export function ConversationChat({ leadId, leadName }: ConversationChatProps) {
  const { data, isLoading } = useConversationMessages(leadId);
  const sendMessage = useSendProspectoMessage();
  const uploadMedia = useMediaUpload();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState("");
  const [pendingFile, setPendingFile] = useState<PendingFile | null>(null);
  const draftStorageKey = `prospectos-draft:${leadId}`;

  const messages = data?.data ?? [];
  const prevMsgCountRef = useRef(0);
  const lastMsgIdRef = useRef<string | null>(null);

  const isBusy = sendMessage.isPending || uploadMedia.isPending;

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
    }, 60);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedDraft = window.sessionStorage.getItem(draftStorageKey);
    setDraft(savedDraft ?? "");
  }, [draftStorageKey]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (draft.trim()) {
      window.sessionStorage.setItem(draftStorageKey, draft);
      return;
    }
    window.sessionStorage.removeItem(draftStorageKey);
  }, [draft, draftStorageKey]);

  // Scroll to bottom when a NEW message arrives
  const lastMsg = messages.length > 0 ? messages[messages.length - 1] : undefined;
  const currentLastId = lastMsg?.id ?? null;
  useEffect(() => {
    if (messages.length === 0) return;
    const isNewMessage =
      messages.length > prevMsgCountRef.current ||
      currentLastId !== lastMsgIdRef.current;
    prevMsgCountRef.current = messages.length;
    lastMsgIdRef.current = currentLastId;
    if (!isNewMessage) return;
    scrollToBottom();
  }, [messages.length, currentLastId, scrollToBottom]);

  // Clean up preview URL on unmount
  useEffect(() => {
    return () => {
      if (pendingFile?.preview) {
        URL.revokeObjectURL(pendingFile.preview);
      }
    };
  }, [pendingFile]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const mediaType = getMediaType(file);
    if (!mediaType) {
      return; // useMediaUpload will show error via notification
    }

    const preview = mediaType === "image" ? URL.createObjectURL(file) : null;
    setPendingFile({ file, mediaType, preview });

    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const clearPendingFile = () => {
    if (pendingFile?.preview) {
      URL.revokeObjectURL(pendingFile.preview);
    }
    setPendingFile(null);
  };

  const handleSend = async () => {
    const text = draft.trim();
    if (!text && !pendingFile) return;
    if (isBusy) return;

    if (pendingFile) {
      // Upload file first, then send reply with media URL
      uploadMedia.mutate(pendingFile.file, {
        onSuccess: (uploadResult) => {
          const replyPayload: Parameters<typeof sendMessage.mutate>[0] = {
            lead_id: leadId,
            media_url: uploadResult.media_url,
            media_type: uploadResult.media_type,
            mimetype: uploadResult.mimetype,
          };
          if (text) replyPayload.message = text;
          if (uploadResult.file_name) replyPayload.file_name = uploadResult.file_name;
          sendMessage.mutate(
            replyPayload,
            {
              onSuccess: () => {
                if (typeof window !== "undefined") {
                  window.sessionStorage.removeItem(draftStorageKey);
                }
                setDraft("");
                clearPendingFile();
                scrollToBottom();
              },
            },
          );
        },
      });
    } else {
      sendMessage.mutate(
        { lead_id: leadId, message: text },
        {
          onSuccess: () => {
            if (typeof window !== "undefined") {
              window.sessionStorage.removeItem(draftStorageKey);
            }
            setDraft("");
            scrollToBottom();
          },
        },
      );
    }
    scrollToBottom();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isLoading) {
    return (
      <Stack gap="sm" p="md">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton
            key={`msg-skel-${i}`}
            height={60}
            radius="lg"
            width={i % 2 === 0 ? "70%" : "60%"}
            ml={i % 2 === 0 ? 0 : "auto"}
          />
        ))}
      </Stack>
    );
  }

  let lastDate = "";

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "var(--mantine-spacing-md)",
        }}
      >
        {messages.length === 0 ? (
          <Stack align="center" justify="center" h="100%" gap="xs">
            <IconBrandWhatsapp size={40} color="var(--mantine-color-gray-4)" />
            <Text size="sm" c="dimmed">
              Sin mensajes en esta conversación
            </Text>
          </Stack>
        ) : (
          <Stack gap="sm">
            {messages.map((msg) => {
              const msgDate = formatDate(msg.created_at);
              const showDateHeader = msgDate !== lastDate;
              lastDate = msgDate;

              return (
                <Box key={msg.id}>
                  {showDateHeader && (
                    <Text size="xs" c="dimmed" ta="center" my="xs" fw={500}>
                      {msgDate}
                    </Text>
                  )}
                  <MessageBubble message={msg} />
                </Box>
              );
            })}
            <div ref={bottomRef} />
          </Stack>
        )}
      </div>

      {/* File preview bar */}
      {pendingFile && (
        <Group
          px="sm"
          py={6}
          gap="xs"
          style={{
            borderTop: "1px solid var(--mantine-color-default-border)",
            backgroundColor: "var(--mantine-color-default)",
          }}
        >
          {pendingFile.preview ? (
            <Image
              src={pendingFile.preview}
              alt="Preview"
              radius="sm"
              w={40}
              h={40}
              fit="cover"
            />
          ) : (
            <Box
              style={{
                width: 40,
                height: 40,
                borderRadius: 4,
                backgroundColor: "var(--mantine-color-default-hover)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {pendingFile.mediaType === "document" && <IconFileText size={20} />}
              {pendingFile.mediaType === "video" && <IconVideo size={20} />}
              {pendingFile.mediaType === "audio" && <IconMicrophone size={20} />}
            </Box>
          )}
          <Stack gap={0} style={{ flex: 1 }}>
            <Text size="xs" fw={500} lineClamp={1}>
              {pendingFile.file.name}
            </Text>
            <Text size="xs" c="dimmed">
              {(pendingFile.file.size / (1024 * 1024)).toFixed(1)} MB
            </Text>
          </Stack>
          <CloseButton size="sm" onClick={clearPendingFile} aria-label="Quitar archivo" />
        </Group>
      )}

      <Group
        p="sm"
        gap="sm"
        style={{
          borderTop: "1px solid var(--mantine-color-default-border)",
          flexShrink: 0,
        }}
        align="flex-end"
      >
        <Textarea
          placeholder="Escribe un mensaje..."
          value={draft}
          onChange={(e) => setDraft(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          autosize
          minRows={1}
          maxRows={4}
          style={{ flex: 1 }}
          disabled={isBusy}
          aria-label="Mensaje al prospecto"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleFileSelect}
          style={{ display: "none" }}
          aria-hidden="true"
        />
        <Tooltip label="Adjuntar archivo" position="top">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="lg"
            onClick={() => fileInputRef.current?.click()}
            disabled={isBusy}
            aria-label="Adjuntar archivo"
          >
            <IconPaperclip size={18} />
          </ActionIcon>
        </Tooltip>
        <OutboundComposer
          leadId={leadId}
          leadName={leadName ?? leadId}
        />
        <ActionIcon
          variant="filled"
          color="green"
          size="lg"
          onClick={handleSend}
          loading={isBusy}
          disabled={!draft.trim() && !pendingFile}
          aria-label="Enviar mensaje"
        >
          <IconSend size={18} />
        </ActionIcon>
      </Group>
    </div>
  );
}
