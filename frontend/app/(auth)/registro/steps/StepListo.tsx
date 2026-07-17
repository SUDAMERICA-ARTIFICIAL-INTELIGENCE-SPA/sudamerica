"use client";

import { useProductos } from "@/hooks/useProductos";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import { plural } from "@/lib/rubros";
import { Button, Card, Group, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import {
  IconArrowRight,
  IconBrandWhatsapp,
  IconCategory2,
  IconCircleCheck,
  IconCreditCard,
  IconToolsKitchen2,
} from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import type { OnboardingStepProps } from "./shared";

export function StepListo(_props: OnboardingStepProps) {
  const router = useRouter();
  const rubro = useRubroLabels();
  const { data: productos } = useProductos({ page: 1, page_size: 1 });
  const { data: whatsapp } = useWhatsAppStatus({ enabled: true });

  const count = productos?.meta.total ?? 0;
  const connected = whatsapp?.status === "open";

  const summary = [
    {
      icon: <IconCategory2 size={18} />,
      label: "Rubro",
      value: `${rubro.emoji} ${rubro.nombre}`,
    },
    {
      icon: <IconToolsKitchen2 size={18} />,
      label: rubro.labels.catalogo,
      value: count > 0 ? `${count} ${plural(rubro.labels.item).toLowerCase()}` : "Pendiente",
    },
    {
      icon: <IconBrandWhatsapp size={18} />,
      label: "WhatsApp",
      value: connected ? "Conectado" : "Pendiente",
    },
  ];

  return (
    <Stack gap="lg" align="center" ta="center">
      <ThemeIcon color="green" size={72} radius="xl" variant="light">
        <IconCircleCheck size={40} />
      </ThemeIcon>
      <Stack gap={4}>
        <Title order={3} c="white">
          ¡Tu negocio está listo!
        </Title>
        <Text c="dimmed">
          Configuramos todo lo esencial. Ya puedes operar desde el panel; lo que falte lo completas
          cuando quieras.
        </Text>
      </Stack>

      <Stack gap="xs" w="100%" maw={420}>
        {summary.map((item) => (
          <Card key={item.label} withBorder radius="md" padding="sm">
            <Group justify="space-between" wrap="nowrap">
              <Group gap="xs">
                <ThemeIcon variant="light" color="indigo" radius="sm" size="md">
                  {item.icon}
                </ThemeIcon>
                <Text size="sm" c="dimmed">
                  {item.label}
                </Text>
              </Group>
              <Text fw={600} size="sm">
                {item.value}
              </Text>
            </Group>
          </Card>
        ))}
      </Stack>

      <Group>
        <Button
          variant="light"
          color="grape"
          leftSection={<IconCreditCard size={16} />}
          onClick={() => router.push("/billing")}
        >
          Ver planes
        </Button>
        <Button
          rightSection={<IconArrowRight size={16} />}
          onClick={() => router.push("/dashboard")}
        >
          Ir al panel
        </Button>
      </Group>
    </Stack>
  );
}
