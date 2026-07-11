"use client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Group, Switch, Text, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconRobot } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

interface AgenteConfig {
  auto_respuesta_whatsapp: boolean;
  outbound_proactivo: boolean;
}

export function AIAutoResponseToggle() {
  const { tenantId } = useAuth();
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["agente-config", tenantId],
    queryFn: () => api.get<AgenteConfig>("/config", { service: "dialer" }),
    enabled: !!tenantId,
  });

  const toggle = useMutation({
    mutationFn: (value: boolean) =>
      api.patch("/config", { auto_respuesta_whatsapp: value }, { service: "dialer" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agente-config", tenantId] });
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo cambiar la configuraci\u00f3n",
        color: "red",
      });
    },
  });

  const toggleOutbound = useMutation({
    mutationFn: (value: boolean) =>
      api.patch("/config", { outbound_proactivo: value }, { service: "dialer" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agente-config", tenantId] });
    },
    onError: () => {
      notifications.show({
        title: "Error",
        message: "No se pudo cambiar la configuraci\u00f3n",
        color: "red",
      });
    },
  });

  if (isLoading || !config) return null;

  return (
    <Group gap="lg">
      <Tooltip label={config.auto_respuesta_whatsapp ? "IA responde autom\u00e1ticamente" : "Solo almacena mensajes, sin respuesta IA"}>
        <Group gap="xs">
          <IconRobot size={16} />
          <Text size="xs" fw={500}>IA Auto</Text>
          <Switch
            size="sm"
            color="green"
            checked={config.auto_respuesta_whatsapp}
            onChange={(e) => toggle.mutate(e.currentTarget.checked)}
            disabled={toggle.isPending}
          />
        </Group>
      </Tooltip>
      <Tooltip label={config.outbound_proactivo ? "Agente env\u00eda mensajes proactivos" : "Solo responde mensajes entrantes"}>
        <Group gap="xs">
          <Text size="xs" fw={500}>Outbound</Text>
          <Switch
            size="sm"
            color="indigo"
            checked={config.outbound_proactivo}
            onChange={(e) => toggleOutbound.mutate(e.currentTarget.checked)}
            disabled={toggleOutbound.isPending}
          />
        </Group>
      </Tooltip>
    </Group>
  );
}
