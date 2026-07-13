"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import { Badge, Card, Group, SimpleGrid, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconBrandInstagram, IconBrandWhatsapp, IconWorld } from "@tabler/icons-react";
import type { ReactNode } from "react";

const CONNECTED_STATES = new Set(["open", "connected", "online"]);

type Canal = {
  nombre: string;
  icon: ReactNode;
  color: string;
  conectado: boolean;
  detalle: string;
  estadoLabel: string;
  estadoColor: string;
};

export default function Page() {
  const { data, isLoading, isError } = useWhatsAppStatus();

  const waStatus = (data?.status ?? "").toLowerCase();
  const waConectado = CONNECTED_STATES.has(waStatus);

  const canales: Canal[] = [
    {
      nombre: "WhatsApp",
      icon: <IconBrandWhatsapp size={22} />,
      color: "green",
      conectado: waConectado,
      detalle: data?.instance_name ? `Instancia: ${data.instance_name}` : "Sin instancia asociada",
      estadoLabel: isError ? "Sin conexión" : waConectado ? "Conectado" : "Desconectado",
      estadoColor: isError ? "gray" : waConectado ? "green" : "red",
    },
    {
      nombre: "Instagram",
      icon: <IconBrandInstagram size={22} />,
      color: "grape",
      conectado: false,
      detalle: "Integración disponible para configurar",
      estadoLabel: "Disponible",
      estadoColor: "blue",
    },
    {
      nombre: "Web",
      icon: <IconWorld size={22} />,
      color: "indigo",
      conectado: false,
      detalle: "Widget de chat para el sitio web",
      estadoLabel: "Disponible",
      estadoColor: "blue",
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader title="Canales" subtitle="Canales de comunicación con tus clientes" />

      <SectionCard title="Canales configurados">
        {isLoading ? (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {[0, 1, 2].map((i) => <Skeleton key={i} height={120} radius="md" />)}
          </SimpleGrid>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {canales.map((c) => (
              <Card key={c.nombre} withBorder radius="md" padding="lg">
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Group gap="sm">
                      <ThemeIcon variant="light" color={c.color} size="lg" radius="md">{c.icon}</ThemeIcon>
                      <Text fw={600}>{c.nombre}</Text>
                    </Group>
                    <Badge variant="light" color={c.estadoColor} radius="sm">{c.estadoLabel}</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">{c.detalle}</Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </SectionCard>
    </Stack>
  );
}
