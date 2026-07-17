"use client";

import { QRModal } from "@/components/prospectos/QRModal";
import { useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import { Alert, Button, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconArrowLeft, IconCircleCheck, IconInfoCircle, IconQrcode } from "@tabler/icons-react";
import { type OnboardingStepProps, nowIso, useSaveOnboarding } from "./shared";

export function StepWhatsApp({ goNext, goBack }: OnboardingStepProps) {
  const save = useSaveOnboarding();
  const [opened, handlers] = useDisclosure(false);
  // Polling suave mientras el modal está cerrado para reflejar el estado actual del vínculo.
  const { data, isLoading } = useWhatsAppStatus({ enabled: true, refetchInterval: 5000 });
  const connected = data?.status === "open";

  async function finish(skipped: boolean) {
    await save.mutateAsync({
      onboarding: {
        required: false,
        completed_at: nowIso(),
        ...(skipped ? { whatsapp_skipped_at: nowIso() } : { whatsapp_completed_at: nowIso() }),
      },
    });
    goNext();
  }

  return (
    <>
      <QRModal opened={opened} onClose={handlers.close} />

      <Stack gap="md">
        <Text c="dimmed" size="sm">
          El momento estrella: vincula el WhatsApp de tu negocio para que el agente empiece a
          atender. Escanea el QR desde <b>WhatsApp → Dispositivos vinculados</b>.
        </Text>

        {connected ? (
          <Alert color="green" radius="md" icon={<IconCircleCheck size={18} />}>
            WhatsApp conectado. Tu agente ya puede recibir mensajes.
          </Alert>
        ) : (
          <Alert
            color={isLoading ? "gray" : "blue"}
            radius="md"
            icon={<IconInfoCircle size={16} />}
          >
            {isLoading
              ? "Revisando estado de la conexión…"
              : "Todavía no hay un número vinculado. Abre el QR para conectarlo (toma menos de un minuto)."}
          </Alert>
        )}

        <Group>
          <Button
            leftSection={connected ? <IconCircleCheck size={16} /> : <IconQrcode size={16} />}
            color={connected ? "green" : "indigo"}
            variant={connected ? "light" : "filled"}
            onClick={handlers.open}
          >
            {connected ? "Ver conexión" : "Conectar por QR"}
          </Button>
        </Group>

        <Group justify="space-between" mt="xs">
          <Button
            variant="subtle"
            color="gray"
            leftSection={<IconArrowLeft size={16} />}
            onClick={goBack}
          >
            Atrás
          </Button>
          <Group gap="xs">
            <Button
              variant="subtle"
              color="gray"
              onClick={() => void finish(true)}
              loading={save.isPending}
            >
              Lo conectaré después
            </Button>
            <Button
              color="green"
              onClick={() => void finish(false)}
              loading={save.isPending}
              disabled={!connected}
              leftSection={
                <ThemeIcon size="xs" variant="transparent" color="white">
                  <IconCircleCheck size={16} />
                </ThemeIcon>
              }
            >
              Finalizar
            </Button>
          </Group>
        </Group>
      </Stack>
    </>
  );
}
