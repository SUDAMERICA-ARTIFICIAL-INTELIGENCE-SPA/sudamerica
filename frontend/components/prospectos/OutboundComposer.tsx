"use client";

import { api } from "@/lib/api";
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Stack,
  Switch,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMessageForward, IconRobot, IconSend } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

interface OutboundComposerProps {
  leadId: string;
  leadName: string;
}

interface OutboundResponse {
  success: boolean;
  message_id: string | null;
  lead_id: string;
}

export function OutboundComposer({ leadId, leadName }: OutboundComposerProps) {
  const [opened, setOpened] = useState(false);
  const [message, setMessage] = useState("");
  const [useAI, setUseAI] = useState(false);
  const queryClient = useQueryClient();

  const sendOutbound = useMutation({
    mutationFn: (payload: { lead_id: string; message: string; use_ai: boolean }) =>
      api.post<OutboundResponse>("/whatsapp/send-outbound", payload, {
        service: "canales",
      }),
    onSuccess: () => {
      notifications.show({
        title: "Enviado",
        message: `Mensaje outbound enviado a ${leadName}`,
        color: "green",
      });
      queryClient.invalidateQueries({ queryKey: ["conversation-messages", leadId] });
      queryClient.invalidateQueries({ queryKey: ["conversation-threads"] });
      setMessage("");
      setOpened(false);
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo enviar el mensaje outbound",
        color: "red",
      });
    },
  });

  const handleSend = () => {
    const text = message.trim();
    if (!text) return;
    sendOutbound.mutate({ lead_id: leadId, message: text, use_ai: useAI });
  };

  return (
    <>
      <ActionIcon
        variant="light"
        color="indigo"
        size="lg"
        onClick={() => setOpened(true)}
        aria-label="Enviar mensaje outbound"
      >
        <IconMessageForward size={18} />
      </ActionIcon>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={`Mensaje outbound a ${leadName}`}
        size="md"
        centered
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Env\u00eda un mensaje proactivo a este prospecto via WhatsApp.
          </Text>

          <Group gap="xs">
            <IconRobot size={16} />
            <Text size="sm">Usar IA para generar respuesta</Text>
            <Switch
              size="sm"
              color="indigo"
              checked={useAI}
              onChange={(e) => setUseAI(e.currentTarget.checked)}
            />
          </Group>

          <Textarea
            label={useAI ? "Contexto para la IA" : "Mensaje"}
            placeholder={
              useAI
                ? "Describe qu\u00e9 quieres comunicar y la IA generar\u00e1 el mensaje..."
                : "Escribe el mensaje que quieres enviar..."
            }
            value={message}
            onChange={(e) => setMessage(e.currentTarget.value)}
            autosize
            minRows={3}
            maxRows={8}
          />

          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setOpened(false)}>
              Cancelar
            </Button>
            <Button
              color="indigo"
              leftSection={<IconSend size={16} />}
              onClick={handleSend}
              loading={sendOutbound.isPending}
              disabled={!message.trim()}
            >
              {useAI ? "Generar y enviar" : "Enviar"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
