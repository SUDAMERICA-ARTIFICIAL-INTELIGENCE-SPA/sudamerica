"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useKDS, useTodayHistory, useTransitionComanda } from "@/hooks/useComandas";
import { useKDSWebSocket } from "@/hooks/useKDSWebSocket";
import { COMANDA_TRANSITIONS, ComandaEstado, TipoEntrega } from "@/lib/enums";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import type { Comanda } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Box,
  Card,
  Collapse,
  Divider,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Tooltip,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconArrowRight,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconClock,
  IconMoped,
  IconShoppingBag,
  IconToolsKitchen2,
  IconWifi,
  IconWifiOff,
  IconX,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";

function getElapsedMinutes(createdAt: string): number {
  return Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
}

function getTimeColor(minutes: number): string {
  if (minutes < 10) return "green";
  if (minutes < 20) return "yellow";
  return "red";
}

function getTipoEntregaIcon(tipo: string) {
  switch (tipo) {
    case TipoEntrega.MESA:
      return <IconToolsKitchen2 size={14} />;
    case TipoEntrega.DELIVERY:
      return <IconMoped size={14} />;
    case TipoEntrega.RETIRO:
      return <IconShoppingBag size={14} />;
    default:
      return null;
  }
}

function getTipoEntregaLabel(tipo: string, mesa: number | null): string {
  switch (tipo) {
    case TipoEntrega.MESA:
      return mesa ? `Mesa ${mesa}` : "Mesa";
    case TipoEntrega.DELIVERY:
      return "Delivery";
    case TipoEntrega.RETIRO:
      return "Retiro";
    default:
      return tipo;
  }
}

function getNextEstado(current: ComandaEstado): ComandaEstado | null {
  const transitions = COMANDA_TRANSITIONS[current];
  // First non-CANCELADO transition
  return transitions.find((t) => t !== ComandaEstado.CANCELADO) ?? null;
}

function ComandaCard({ comanda }: { comanda: Comanda }) {
  const { mutate: transition, isPending } = useTransitionComanda();
  const elapsed = getElapsedMinutes(comanda.created_at);
  const timeColor = getTimeColor(elapsed);
  const nextEstado = getNextEstado(comanda.estado as ComandaEstado);
  const canCancel = COMANDA_TRANSITIONS[comanda.estado as ComandaEstado]?.includes(
    ComandaEstado.CANCELADO,
  );

  const total = comanda.items.reduce((sum, item) => sum + Number(item.subtotal), 0);

  return (
    <Card
      shadow="sm"
      radius="md"
      p="sm"
      withBorder
      style={{
        borderLeft: `4px solid var(--mantine-color-${timeColor}-6)`,
      }}
    >
      {/* Header */}
      <Group justify="space-between" mb="xs" wrap="nowrap">
        <Group gap={6} wrap="nowrap">
          <Badge
            size="sm"
            variant="light"
            color="blue"
            leftSection={getTipoEntregaIcon(comanda.tipo_entrega)}
          >
            {getTipoEntregaLabel(comanda.tipo_entrega, comanda.numero_mesa)}
          </Badge>
          <Badge size="xs" variant="dot" color={timeColor}>
            <IconClock size={10} style={{ marginRight: 2 }} />
            {elapsed}m
          </Badge>
        </Group>
        {comanda.prioridad > 0 && (
          <Badge size="xs" color="red" variant="filled">
            URGENTE
          </Badge>
        )}
      </Group>

      {/* Client name */}
      {comanda.cliente_nombre && (
        <Text fz={12} c="dimmed" mb={4}>
          {comanda.cliente_nombre}
        </Text>
      )}

      {/* Items */}
      <Stack gap={4} mb="xs">
        {comanda.items.map((item) => (
          <Box key={item.id}>
            <Group justify="space-between" wrap="nowrap">
              <Text fz={13} fw={600} truncate="end" style={{ flex: 1 }}>
                {item.cantidad > 1 ? `${item.cantidad}x ` : ""}
                {item.producto_nombre ?? "Producto"}
              </Text>
              <Text fz={12} c="dimmed">
                ${Number(item.subtotal).toLocaleString()}
              </Text>
            </Group>
            {item.modifiers_json.length > 0 && (
              <Text fz={11} c="dimmed" ml="xs">
                {item.modifiers_json.map((m) => m.nombre).join(", ")}
              </Text>
            )}
            {item.notas && (
              <Text fz={11} c="yellow" ml="xs" fs="italic">
                {item.notas}
              </Text>
            )}
          </Box>
        ))}
      </Stack>

      {/* Notes */}
      {comanda.notas && (
        <Text fz={11} c="yellow" mb="xs" fs="italic">
          {comanda.notas}
        </Text>
      )}

      {/* Footer: total + actions */}
      <Group justify="space-between" mt="xs">
        <Text fz={13} fw={700}>
          ${total.toLocaleString()}
        </Text>
        <Group gap={4}>
          {canCancel && (
            <Tooltip label="Cancelar" position="top">
              <ActionIcon
                size="sm"
                color="red"
                variant="subtle"
                loading={isPending}
                onClick={() => transition({ id: comanda.id, estado: ComandaEstado.CANCELADO })}
                aria-label="Cancelar comanda"
              >
                <IconX size={14} />
              </ActionIcon>
            </Tooltip>
          )}
          {nextEstado && (
            <Tooltip
              label={
                nextEstado === ComandaEstado.EN_COCINA
                  ? "Iniciar preparación"
                  : nextEstado === ComandaEstado.LISTO
                    ? "Marcar como listo"
                    : "Marcar como entregado"
              }
              position="top"
            >
              <ActionIcon
                size="md"
                color={nextEstado === ComandaEstado.ENTREGADO ? "green" : "indigo"}
                variant="filled"
                loading={isPending}
                onClick={() => transition({ id: comanda.id, estado: nextEstado })}
                aria-label={`Avanzar a ${nextEstado}`}
              >
                {nextEstado === ComandaEstado.ENTREGADO ? (
                  <IconCheck size={16} />
                ) : (
                  <IconArrowRight size={16} />
                )}
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      </Group>
    </Card>
  );
}

function KDSColumn({
  title,
  color,
  comandas,
  isLoading,
}: {
  title: string;
  color: string;
  comandas: Comanda[];
  isLoading: boolean;
}) {
  return (
    <Box aria-label={`Columna: ${title}`}>
      <Paper
        p="sm"
        radius="md"
        mb="sm"
        style={{
          backgroundColor: `var(--mantine-color-${color}-light)`,
          border: `1px solid var(--mantine-color-${color}-light-hover)`,
        }}
      >
        <Group gap="xs" align="center">
          <Badge color={color} variant="filled" size="xs" circle aria-hidden="true">
            {comandas.length}
          </Badge>
          <Text
            style={{
              ...TYPOGRAPHY.sectionLabel,
              color: `var(--mantine-color-${color}-light-color)`,
            }}
          >
            {title}
          </Text>
        </Group>
      </Paper>
      <Stack gap="sm">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={`skel-${title}-${i}`} height={160} radius="md" />
            ))
          : comandas.map((c) => <ComandaCard key={c.id} comanda={c} />)}
        {!isLoading && comandas.length === 0 && <EmptyState icon="🍽️" title="Sin comandas" />}
      </Stack>
    </Box>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
}

function TodayHistory() {
  const { data, isLoading } = useTodayHistory();
  const [opened, { toggle }] = useDisclosure(false);

  const entregados = data?.entregados ?? [];
  const cancelados = data?.cancelados ?? [];
  const total = entregados.length + cancelados.length;

  if (isLoading) return <Skeleton height={40} radius="md" />;
  if (total === 0) return null;

  const allOrders = [
    ...entregados.map((c) => ({ ...c, _status: "ENTREGADO" as const })),
    ...cancelados.map((c) => ({ ...c, _status: "CANCELADO" as const })),
  ].sort(
    (a, b) =>
      new Date(b.entregado_at ?? b.updated_at).getTime() -
      new Date(a.entregado_at ?? a.updated_at).getTime(),
  );

  return (
    <Stack gap="sm">
      <UnstyledButton onClick={toggle}>
        <Group gap="xs">
          {opened ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
          <Text fw={600} fz="sm">
            Historial (últimas 24h)
          </Text>
          <Badge size="sm" variant="light" color="gray" circle>
            {total}
          </Badge>
          <Badge size="xs" variant="light" color="green">
            {entregados.length} entregados
          </Badge>
          {cancelados.length > 0 && (
            <Badge size="xs" variant="light" color="red">
              {cancelados.length} cancelados
            </Badge>
          )}
        </Group>
      </UnstyledButton>
      <Collapse in={opened}>
        <Table horizontalSpacing="sm" verticalSpacing={6} fz="sm" striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Hora</Table.Th>
              <Table.Th>Tipo</Table.Th>
              <Table.Th>Items</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Total</Table.Th>
              <Table.Th>Estado</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {allOrders.map((c) => {
              const orderTotal = c.items.reduce((s, i) => s + Number(i.subtotal), 0);
              return (
                <Table.Tr key={c.id}>
                  <Table.Td>
                    <Text fz={12}>{formatTime(c.entregado_at ?? c.updated_at)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="xs" variant="light" color="blue">
                      {getTipoEntregaLabel(c.tipo_entrega, c.numero_mesa)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fz={12} lineClamp={1}>
                      {c.items
                        .map(
                          (i) =>
                            `${i.cantidad > 1 ? `${i.cantidad}x ` : ""}${i.producto_nombre ?? "?"}`,
                        )
                        .join(", ")}
                    </Text>
                  </Table.Td>
                  <Table.Td className="num-tabular">
                    <Text fz={12} fw={600}>
                      ${orderTotal.toLocaleString()}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      size="xs"
                      variant="filled"
                      color={c._status === "ENTREGADO" ? "green" : "red"}
                    >
                      {c._status === "ENTREGADO" ? "Entregado" : "Cancelado"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Collapse>
    </Stack>
  );
}

/**
 * Play a short notification sound when a new comanda arrives.
 * Uses the Web Audio API to synthesize a two-tone chime — no audio file needed.
 */
function playNewComandaSound(): void {
  try {
    const ctx = new AudioContext();
    const now = ctx.currentTime;

    // First tone (C5)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.value = 523.25;
    gain1.gain.setValueAtTime(0.3, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
    osc1.connect(gain1).connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.2);

    // Second tone (E5)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.value = 659.25;
    gain2.gain.setValueAtTime(0.3, now + 0.15);
    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
    osc2.connect(gain2).connect(ctx.destination);
    osc2.start(now + 0.15);
    osc2.stop(now + 0.4);

    // Clean up context after sounds finish
    setTimeout(() => void ctx.close(), 500);
  } catch {
    // AudioContext not available (e.g., SSR, strict autoplay policy)
  }
}

export function KDSBoard() {
  const { isConnected } = useKDSWebSocket();
  const { data, isLoading } = useKDS({ wsConnected: isConnected });
  const [flash, setFlash] = useState(false);
  const flashTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleNewComanda = useCallback(() => {
    playNewComandaSound();
    setFlash(true);
    if (flashTimeoutRef.current) clearTimeout(flashTimeoutRef.current);
    flashTimeoutRef.current = setTimeout(() => setFlash(false), 600);
  }, []);

  // Listen for "kds:new-comanda" custom event dispatched by the WS hook
  useEffect(() => {
    const handler = () => handleNewComanda();
    window.addEventListener("kds:new-comanda", handler);
    return () => {
      window.removeEventListener("kds:new-comanda", handler);
      if (flashTimeoutRef.current) clearTimeout(flashTimeoutRef.current);
    };
  }, [handleNewComanda]);

  const pendientes = data?.PENDIENTE ?? [];
  const enCocina = data?.EN_COCINA ?? [];
  const listos = data?.LISTO ?? [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Cocina — KDS"
        actions={
          <>
            <Tooltip
              label={isConnected ? "Tiempo real conectado" : "Reconectando..."}
              position="left"
            >
              <Badge
                size="sm"
                variant="dot"
                color={isConnected ? "green" : "red"}
                leftSection={isConnected ? <IconWifi size={12} /> : <IconWifiOff size={12} />}
              >
                {isConnected ? "En vivo" : "Offline"}
              </Badge>
            </Tooltip>
            <Badge size="lg" variant="light" color="gray">
              {pendientes.length + enCocina.length + listos.length} activas
            </Badge>
          </>
        }
      />

      <Box
        style={{
          transition: "background-color 0.3s ease-out",
          backgroundColor: flash ? "var(--mantine-color-yellow-1)" : "transparent",
          borderRadius: "var(--mantine-radius-md)",
          padding: flash ? 4 : 0,
        }}
      >
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
          <KDSColumn title="Pendiente" color="yellow" comandas={pendientes} isLoading={isLoading} />
          <KDSColumn title="En Cocina" color="orange" comandas={enCocina} isLoading={isLoading} />
          <KDSColumn title="Listo" color="green" comandas={listos} isLoading={isLoading} />
        </SimpleGrid>
      </Box>

      <Divider />
      <TodayHistory />
    </Stack>
  );
}
