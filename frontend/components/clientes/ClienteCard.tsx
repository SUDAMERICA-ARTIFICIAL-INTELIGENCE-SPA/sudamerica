"use client";

import {
  ClienteEstado,
  CLIENTE_ESTADO_COLORS,
  CLIENTE_ESTADO_LABELS,
} from "@/lib/enums";
import type { Lead } from "@/lib/types";
import { Badge, Card, Group, Stack, Text } from "@mantine/core";
import {
  IconCalendarEvent,
  IconCash,
  IconClockHour4,
  IconShoppingCart,
  IconToolsKitchen2,
} from "@tabler/icons-react";

interface ClienteCardProps {
  lead: Lead;
  onClick?: (lead: Lead) => void;
}

function formatCurrency(value: number): string {
  return `$${Intl.NumberFormat("es-CL").format(value)}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Sin registro";
  return new Date(dateStr).toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function ClienteCard({ lead, onClick }: ClienteCardProps) {
  const estadoCliente = (lead.estado_cliente as ClienteEstado) ?? ClienteEstado.NUEVO;
  const color = CLIENTE_ESTADO_COLORS[estadoCliente] ?? "gray";
  const label = CLIENTE_ESTADO_LABELS[estadoCliente] ?? estadoCliente;

  return (
    <Card
      shadow="sm"
      padding="lg"
      radius={12}
      withBorder
      style={{ cursor: onClick ? "pointer" : "default" }}
      onClick={() => onClick?.(lead)}
      aria-label={`Ficha de cliente ${lead.nombre}`}
    >
      <Stack gap="sm">
        {/* Header: Name + Estado badge */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Text fw={600} size="md">
              {lead.nombre}
            </Text>
            {lead.email && (
              <Text size="xs" c="dimmed">
                {lead.email}
              </Text>
            )}
          </div>
          <Badge color={color} variant="light" size="sm" radius="sm">
            {label}
          </Badge>
        </Group>

        {/* Plato favorito */}
        {lead.plato_favorito && (
          <Group gap="xs">
            <IconToolsKitchen2 size={14} color="var(--mantine-color-orange-6)" />
            <Text size="sm" c="dimmed">
              Favorito:
            </Text>
            <Text size="sm" fw={500}>
              {lead.plato_favorito}
            </Text>
          </Group>
        )}

        {/* Stats row */}
        <Group gap="lg" wrap="wrap">
          {/* Frecuencia */}
          {lead.frecuencia_dias != null && (
            <Group gap={4}>
              <IconClockHour4 size={14} color="var(--mantine-color-teal-6)" />
              <Text size="xs" c="dimmed">
                Cada {lead.frecuencia_dias} dias
              </Text>
            </Group>
          )}

          {/* Total gastado */}
          <Group gap={4}>
            <IconCash size={14} color="var(--mantine-color-green-6)" />
            <Text size="xs" fw={500}>
              {formatCurrency(lead.total_gastado)}
            </Text>
          </Group>

          {/* Total pedidos */}
          <Group gap={4}>
            <IconShoppingCart size={14} color="var(--mantine-color-indigo-6)" />
            <Text size="xs" c="dimmed">
              {lead.total_pedidos} pedidos
            </Text>
          </Group>
        </Group>

        {/* Ultima visita */}
        <Group gap={4}>
          <IconCalendarEvent size={14} color="var(--mantine-color-gray-6)" />
          <Text size="xs" c="dimmed">
            Ultima visita: {formatDate(lead.ultima_visita)}
          </Text>
        </Group>

        {/* Tags */}
        {lead.tags && lead.tags.length > 0 && (
          <Group gap={4}>
            {lead.tags.map((tag) => (
              <Badge key={tag} variant="dot" size="xs" color="gray">
                {tag}
              </Badge>
            ))}
          </Group>
        )}
      </Stack>
    </Card>
  );
}
