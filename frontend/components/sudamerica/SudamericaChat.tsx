"use client";

import type { SudamericaMessage } from "@/hooks/useSudamericaChat";
import { useSudamericaChat } from "@/hooks/useSudamericaChat";
import { useSudamericaSend } from "@/hooks/useSudamericaSend";
import {
  ActionIcon,
  Badge,
  Box,
  CloseButton,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from "@mantine/core";
import {
  IconFile,
  IconPaperclip,
  IconPhoto,
  IconSend,
  IconSparkles,
  IconUser,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { MarkdownMessage } from "./MarkdownMessage";

const CONTROL_CHARS_RE = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;

const ACCEPTED_TYPES =
  "image/png,image/jpeg,image/webp,image/gif,application/pdf,text/csv," +
  "application/vnd.ms-excel," +
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function sanitizeContent(text: string): string {
  return text.replace(CONTROL_CHARS_RE, "");
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

function isImageType(ct: string): boolean {
  return ct.startsWith("image/");
}

function FileIcon({ contentType }: { contentType: string }) {
  if (isImageType(contentType)) return <IconPhoto size={14} />;
  return <IconFile size={14} />;
}

function MessageBubble({ message }: { message: SudamericaMessage }) {
  const isAssistant = message.role === "assistant";

  return (
    <Box
      style={{
        display: "flex",
        justifyContent: isAssistant ? "flex-start" : "flex-end",
        paddingRight: isAssistant ? 48 : 0,
        paddingLeft: isAssistant ? 0 : 48,
      }}
    >
      <Paper
        p="sm"
        radius="lg"
        style={{
          backgroundColor: isAssistant
            ? "var(--mantine-color-violet-light)"
            : "var(--mantine-color-default)",
          borderBottomLeftRadius: isAssistant ? 4 : undefined,
          borderBottomRightRadius: isAssistant ? undefined : 4,
          maxWidth: "85%",
          border: isAssistant ? undefined : "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group gap={4} mb={4}>
          {isAssistant ? (
            <IconSparkles size={14} color="var(--mantine-color-violet-light-color)" />
          ) : (
            <IconUser size={14} color="var(--mantine-color-indigo-5)" />
          )}
          <Text size="xs" fw={600} c={isAssistant ? "violet" : "indigo"}>
            {isAssistant ? "Sudamérica AI" : "Tu"}
          </Text>
        </Group>
        {isAssistant ? (
          <MarkdownMessage content={sanitizeContent(message.content)} />
        ) : (
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
            {sanitizeContent(message.content)}
          </Text>
        )}
        <Group justify="flex-end" gap="xs" mt={4}>
          {isAssistant && message.tokens_used ? (
            <Badge size="xs" variant="dot" color="gray">
              {message.tokens_used} tokens
            </Badge>
          ) : null}
          <Text size="xs" c="dimmed">
            {formatTime(message.created_at)}
          </Text>
        </Group>
      </Paper>
    </Box>
  );
}

export function SudamericaChat() {
  const { data, isLoading } = useSudamericaChat();
  const sendMessage = useSudamericaSend();
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);

  const messages = data?.data ?? [];
  const prevMsgCountRef = useRef(0);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
    }, 60);
  }, []);

  useEffect(() => {
    if (messages.length > prevMsgCountRef.current) {
      scrollToBottom();
    }
    prevMsgCountRef.current = messages.length;
  }, [messages.length, scrollToBottom]);

  const handleSend = () => {
    const text = draft.trim();
    if ((!text && !attachedFile) || sendMessage.isPending) return;
    const msg = text || (attachedFile ? `Analiza este archivo: ${attachedFile.name}` : "");
    sendMessage.mutate(
      { message: msg, file: attachedFile },
      {
        onSuccess: () => {
          setDraft("");
          setAttachedFile(null);
          scrollToBottom();
        },
      },
    );
    scrollToBottom();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachedFile(file);
    }
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  if (isLoading) {
    return (
      <Stack gap="sm" p="md">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton
            key={`sudamerica-skel-${i}`}
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
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "var(--mantine-spacing-md)",
        }}
      >
        {messages.length === 0 ? (
          <Stack align="center" justify="center" h="100%" gap="xs">
            <IconSparkles size={48} color="var(--mantine-color-violet-4)" />
            <Text size="lg" fw={600} c="violet">
              Sudamérica AI
            </Text>
            <Text size="sm" c="dimmed" ta="center" maw={400}>
              Tu copiloto administrativo. Preguntame sobre ventas, menu, clientes, metricas o pedeme
              que cambie precios y disponibilidad.
            </Text>
            <Text size="xs" c="dimmed" ta="center" maw={350} mt={4}>
              Puedes adjuntar imagenes de tu carta, PDFs o archivos CSV para que los analice y cree
              productos automaticamente.
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

      {/* Attached file preview */}
      {attachedFile && (
        <Group
          px="sm"
          py={4}
          gap="xs"
          style={{
            borderTop: "1px solid var(--mantine-color-default-border)",
            backgroundColor: "var(--mantine-color-violet-light)",
          }}
        >
          <FileIcon contentType={attachedFile.type} />
          <Text size="xs" fw={500} truncate="end" style={{ flex: 1 }}>
            {attachedFile.name}
          </Text>
          <Text size="xs" c="dimmed">
            {(attachedFile.size / 1024).toFixed(0)} KB
          </Text>
          <CloseButton
            size="xs"
            onClick={() => setAttachedFile(null)}
            aria-label="Quitar archivo"
          />
        </Group>
      )}

      {/* Input area */}
      <Group
        p="sm"
        gap="sm"
        style={{
          borderTop: attachedFile ? undefined : "1px solid var(--mantine-color-default-border)",
          flexShrink: 0,
        }}
        align="flex-end"
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          style={{ display: "none" }}
          onChange={handleFileSelect}
        />

        {/* Attach button */}
        <Tooltip label="Adjuntar archivo (imagen, PDF, CSV)" position="top" withArrow>
          <ActionIcon
            variant="subtle"
            color="gray"
            size="lg"
            onClick={() => fileInputRef.current?.click()}
            disabled={sendMessage.isPending}
            aria-label="Adjuntar archivo"
          >
            <IconPaperclip size={18} />
          </ActionIcon>
        </Tooltip>

        <Textarea
          placeholder={
            attachedFile ? `Mensaje sobre ${attachedFile.name}...` : "Pregunta a Sudamérica AI..."
          }
          value={draft}
          onChange={(e) => setDraft(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          autosize
          minRows={1}
          maxRows={4}
          style={{ flex: 1 }}
          disabled={sendMessage.isPending}
          aria-label="Mensaje a Sudamérica AI"
        />
        <ActionIcon
          variant="filled"
          color="violet"
          size="lg"
          onClick={handleSend}
          loading={sendMessage.isPending}
          disabled={!draft.trim() && !attachedFile}
          aria-label="Enviar mensaje"
        >
          <IconSend size={18} />
        </ActionIcon>
      </Group>
    </div>
  );
}
