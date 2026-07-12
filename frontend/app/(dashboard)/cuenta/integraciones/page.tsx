"use client";

import { QRModal } from "@/components/prospectos/QRModal";
import { WhatsAppStatus } from "@/components/prospectos/WhatsAppStatus";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Group, SimpleGrid, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconBrandWhatsapp, IconCreditCard, IconWebhook } from "@tabler/icons-react";

/**
 * Integraciones — canales conectados a la cuenta. El canal WhatsApp reusa el
 * onboarding real de prospectos (WhatsAppStatus + QRModal, canales-service);
 * Pagos y Webhooks aún no tienen backend propio.
 */
export default function IntegracionesPage() {
  const [qrOpened, { open: openQR, close: closeQR }] = useDisclosure(false);

  return (
    <>
      <QRModal opened={qrOpened} onClose={closeQR} />
      <Stack gap="lg">
        <PageHeader
          title="Integraciones"
          subtitle="Conecta canales de mensajería, pagos y webhooks con tu negocio."
        />
        <SectionCard
          title="Canales"
          subtitle="Estado de conexión de tus canales de atención al cliente."
        >
          <Group justify="space-between" wrap="wrap" gap="md">
            <Group gap="sm" wrap="nowrap">
              <IconBrandWhatsapp size={24} aria-hidden="true" />
              <div>
                <Text size="sm" fw={600}>
                  WhatsApp Business
                </Text>
                <Text size="xs" c="dimmed">
                  Canal principal de conversaciones con tus clientes.
                </Text>
              </div>
            </Group>
            <WhatsAppStatus onConnectClick={openQR} />
          </Group>
        </SectionCard>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          <SectionCard title="Pagos" fullHeight>
            <EmptyState
              icon={<IconCreditCard size={40} />}
              title="En construcción"
              description="Pronto vas a conectar pasarelas de pago (links, tarjetas, POS) desde aquí."
            />
          </SectionCard>
          <SectionCard title="Webhooks" fullHeight>
            <EmptyState
              icon={<IconWebhook size={40} />}
              title="En construcción"
              description="Pronto vas a suscribir sistemas externos a los eventos de tu cuenta desde aquí."
            />
          </SectionCard>
        </SimpleGrid>
      </Stack>
    </>
  );
}
