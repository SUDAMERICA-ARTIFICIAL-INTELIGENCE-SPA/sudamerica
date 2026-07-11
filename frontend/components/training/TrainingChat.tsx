"use client";

import { useTestAI } from "@/hooks/useTraining";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Paper,
  ScrollArea,
  Skeleton,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { IconSend, IconTrash } from "@tabler/icons-react";
import { useCallback, useRef, useState } from "react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export function TrainingChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const testAI = useTestAI();
  const viewport = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      viewport.current?.scrollTo({
        top: viewport.current.scrollHeight,
        behavior: "smooth",
      });
    }, 50);
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || testAI.isPending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    scrollToBottom();

    testAI.mutate(trimmed, {
      onSuccess: (data) => {
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          text: data.response,
        };
        setMessages((prev) => [...prev, aiMsg]);
        scrollToBottom();
      },
    });
  }, [input, testAI, scrollToBottom]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleClear = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <Paper withBorder radius="md" p="md" style={{ display: "flex", flexDirection: "column", height: 420 }}>
      <Group justify="space-between" mb="xs">
        <Text fw={600} fz="sm">
          Chat de prueba
        </Text>
        {messages.length > 0 && (
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            onClick={handleClear}
            aria-label="Limpiar chat"
          >
            <IconTrash size={14} />
          </ActionIcon>
        )}
      </Group>

      <ScrollArea style={{ flex: 1 }} viewportRef={viewport} offsetScrollbars>
        <Stack gap="xs">
          {messages.length === 0 && (
            <Text c="dimmed" fz="sm" ta="center" py="xl">
              Escribe un mensaje para probar la IA con tu conocimiento actual.
            </Text>
          )}

          {messages.map((msg) => (
            <Box
              key={msg.id}
              style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "85%",
              }}
            >
              <Paper
                radius="lg"
                px="sm"
                py={6}
                style={{
                  backgroundColor:
                    msg.role === "user"
                      ? "var(--mantine-color-indigo-6)"
                      : "var(--mantine-color-gray-1)",
                }}
              >
                <Text
                  fz="sm"
                  c={msg.role === "user" ? "white" : "dark"}
                  style={{ whiteSpace: "pre-wrap" }}
                >
                  {msg.text}
                </Text>
              </Paper>
            </Box>
          ))}

          {testAI.isPending && (
            <Box style={{ alignSelf: "flex-start", maxWidth: "85%" }}>
              <Stack gap={4}>
                <Skeleton height={12} width={200} radius="xl" />
                <Skeleton height={12} width={150} radius="xl" />
              </Stack>
            </Box>
          )}
        </Stack>
      </ScrollArea>

      <Group gap="xs" mt="xs">
        <TextInput
          placeholder="Escribe una pregunta de prueba..."
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          style={{ flex: 1 }}
          disabled={testAI.isPending}
          aria-label="Mensaje de prueba"
        />
        <Button
          onClick={handleSend}
          loading={testAI.isPending}
          disabled={!input.trim()}
          leftSection={<IconSend size={16} />}
          aria-label="Enviar mensaje de prueba"
        >
          Probar
        </Button>
      </Group>
    </Paper>
  );
}
