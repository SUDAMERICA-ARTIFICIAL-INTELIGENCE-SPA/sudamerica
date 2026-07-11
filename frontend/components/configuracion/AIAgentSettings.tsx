"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { useAgenteConfigs, useUpdateAgenteConfig } from "@/hooks/useAgenteConfig";
import { SubAgenteType } from "@/lib/enums";
import type { AgenteConfig } from "@/lib/types";
import {
  Badge,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Text,
  ThemeIcon,
} from "@mantine/core";
import { IconBook, IconBrain, IconCurrencyDollar, IconMessageChatbot } from "@tabler/icons-react";

const AGENTE_META: Record<
  SubAgenteType,
  { label: string; description: string; icon: React.ReactNode; color: string }
> = {
  [SubAgenteType.RAG]: {
    label: "RAG — Base de conocimiento",
    description: "Responde preguntas usando documentos internos y FAQs vectorizados.",
    icon: <IconBook size={20} />,
    color: "indigo",
  },
  [SubAgenteType.COTIZADOR]: {
    label: "Cotizador automático",
    description: "Genera y envía presupuestos personalizados basados en el catálogo de productos.",
    icon: <IconCurrencyDollar size={20} />,
    color: "orange",
  },
  [SubAgenteType.SEGUIMIENTO]: {
    label: "Seguimiento de leads",
    description: "Retoma automáticamente conversaciones inactivas y programa recordatorios.",
    icon: <IconMessageChatbot size={20} />,
    color: "teal",
  },
  [SubAgenteType.FAQ]: {
    label: "FAQ — Preguntas frecuentes",
    description: "Resuelve consultas frecuentes sin intervención humana (horarios, precios, etc.).",
    icon: <IconBrain size={20} />,
    color: "violet",
  },
};

interface AgentCardProps {
  config: AgenteConfig;
}

function AgentCard({ config }: AgentCardProps) {
  const { mutate: update, isPending } = useUpdateAgenteConfig();
  const meta = AGENTE_META[config.tipo] ?? {
    label: config.tipo,
    description: "",
    icon: <IconBrain size={20} />,
    color: "gray",
  };

  function handleToggle(checked: boolean) {
    update({ tipo: config.tipo, dto: { activo: checked } });
  }

  return (
    <Paper
      p="md"
      radius="md"
      withBorder
      style={{
        borderColor: config.activo
          ? `var(--mantine-color-${meta.color}-3)`
          : "var(--mantine-color-default-border)",
        transition: "border-color 200ms ease-out",
      }}
      aria-label={`Sub-agente: ${meta.label}`}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Group gap="sm" align="flex-start" wrap="nowrap" style={{ flex: 1 }}>
          <ThemeIcon
            color={config.activo ? meta.color : "gray"}
            variant="light"
            size="lg"
            radius="md"
            aria-hidden="true"
          >
            {meta.icon}
          </ThemeIcon>
          <Stack gap={4} style={{ flex: 1 }}>
            <Group gap="xs" align="center">
              <Text size="sm" fw={600}>
                {meta.label}
              </Text>
              <Badge color={config.activo ? meta.color : "gray"} variant="light" size="xs">
                {config.activo ? "Activo" : "Inactivo"}
              </Badge>
            </Group>
            <Text size="xs" c="dimmed" lineClamp={2}>
              {meta.description}
            </Text>
          </Stack>
        </Group>
        <Switch
          checked={config.activo}
          onChange={(e) => handleToggle(e.currentTarget.checked)}
          disabled={isPending}
          color={meta.color}
          size="md"
          aria-label={`${config.activo ? "Desactivar" : "Activar"} ${meta.label}`}
        />
      </Group>
    </Paper>
  );
}

// Default configs when API returns nothing (all tipos required)
const ALL_TIPOS = Object.values(SubAgenteType);

function mergeWithDefaults(configs: AgenteConfig[]): AgenteConfig[] {
  return ALL_TIPOS.map((tipo) => {
    const existing = configs.find((c) => c.tipo === tipo);
    return (
      existing ?? {
        id: tipo,
        tenant_id: "",
        tipo,
        activo: false,
        config: {},
        updated_at: new Date().toISOString(),
      }
    );
  });
}

export function AIAgentSettings() {
  const { data: configs, isLoading } = useAgenteConfigs();

  if (isLoading) {
    return (
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} height={100} radius="md" />
        ))}
      </SimpleGrid>
    );
  }

  const merged = mergeWithDefaults(configs ?? []);

  if (merged.length === 0) {
    return (
      <EmptyState
        icon="🤖"
        title="Sin agentes configurados"
        description="No se encontraron sub-agentes de IA."
      />
    );
  }

  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md" aria-label="Configuración de sub-agentes IA">
      {merged.map((config) => (
        <AgentCard key={config.tipo} config={config} />
      ))}
    </SimpleGrid>
  );
}
