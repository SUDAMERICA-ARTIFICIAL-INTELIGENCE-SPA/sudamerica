"use client";

import { useDisconnectWhatsApp, useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import { CHART_COLORS } from "@/lib/chart-config";
import { Badge, Button, Group, Skeleton, Text } from "@mantine/core";
import { modals } from "@mantine/modals";
import { IconBrandWhatsapp, IconPlugConnectedX, IconRefresh } from "@tabler/icons-react";

interface WhatsAppStatusProps {
  onConnectClick: () => void;
}

export function WhatsAppStatus({ onConnectClick }: WhatsAppStatusProps) {
  const { data, isLoading, refetch } = useWhatsAppStatus();
  const disconnect = useDisconnectWhatsApp();

  if (isLoading) {
    return <Skeleton height={40} radius="md" />;
  }

  const status = data?.status ?? "unknown";
  const isConnected = status === "open";

  const handleDisconnect = () => {
    modals.openConfirmModal({
      title: "Desconectar WhatsApp",
      children: (
        <Text size="sm">
          Se cerrará la sesión de WhatsApp. Podrás conectar otro número después. Las conversaciones
          existentes se mantienen.
        </Text>
      ),
      labels: { confirm: "Desconectar", cancel: "Cancelar" },
      confirmProps: { color: "red" },
      onConfirm: () => disconnect.mutate(),
    });
  };

  return (
    <Group gap="sm">
      <IconBrandWhatsapp
        size={20}
        color={isConnected ? CHART_COLORS.success : CHART_COLORS.neutral}
      />
      <Text size="sm" fw={500}>
        WhatsApp
      </Text>
      <Badge color={isConnected ? "green" : "gray"} variant="light" size="sm">
        {isConnected ? "Conectado" : "Desconectado"}
      </Badge>
      {!isConnected && (
        <Button
          size="xs"
          variant="filled"
          color="green"
          leftSection={<IconBrandWhatsapp size={14} />}
          onClick={onConnectClick}
        >
          Conectar
        </Button>
      )}
      {isConnected && (
        <Group gap="xs">
          <Button
            size="xs"
            variant="subtle"
            color="gray"
            leftSection={<IconRefresh size={14} />}
            onClick={() => refetch()}
          >
            Verificar
          </Button>
          <Button
            size="xs"
            variant="light"
            color="red"
            leftSection={<IconPlugConnectedX size={14} />}
            onClick={handleDisconnect}
            loading={disconnect.isPending}
          >
            Desconectar
          </Button>
        </Group>
      )}
    </Group>
  );
}
