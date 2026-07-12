"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useCreateBillingCheckout } from "@/hooks/useBilling";
import { useTenant } from "@/hooks/useTenant";
import { TenantPlan } from "@/lib/enums";
import { normalizeTenantPlan } from "@/lib/onboarding";
import { TYPOGRAPHY } from "@/lib/theme-tokens";
import { Alert, Badge, Button, Card, Group, Loader, SimpleGrid, Stack, Text } from "@mantine/core";
import {
  IconAlertCircle,
  IconCheck,
  IconCreditCard,
  IconRocket,
  IconUsersGroup,
} from "@tabler/icons-react";
import { useSearchParams } from "next/navigation";

type PaidPlan = TenantPlan.PLUS | TenantPlan.PRO;

const PLAN_CARDS: Array<{
  plan: TenantPlan;
  title: string;
  badgeColor: string;
  price: string;
  priceDetail: string;
  popular?: boolean;
  description: string;
  users: string;
  contacts: string;
  bullets: string[];
}> = [
  {
    plan: TenantPlan.ESTANDAR,
    title: "Emprendedor",
    badgeColor: "gray",
    price: "$0",
    priceDetail: "gratis para siempre",
    description: "Base operativa para comenzar a tomar pedidos y atender WhatsApp.",
    users: "3 usuarios",
    contacts: "100 clientes/mes",
    bullets: ["WhatsApp + KDS en tiempo real", "Carta y modificadores", "Dashboard operativo"],
  },
  {
    plan: TenantPlan.PLUS,
    title: "Crecimiento",
    badgeColor: "blue",
    price: "$29.990",
    priceDetail: "CLP/mes +IVA",
    popular: true,
    description: "Escala el equipo y aumenta la capacidad comercial del restaurante.",
    users: "8 usuarios",
    contacts: "500 clientes/mes",
    bullets: [
      "Mayor capacidad mensual",
      "Más personal operativo",
      "Suscripción automática vía Mercado Pago",
    ],
  },
  {
    plan: TenantPlan.PRO,
    title: "Corporativo",
    badgeColor: "grape",
    price: "$74.990",
    priceDetail: "CLP/mes +IVA",
    description:
      "Capacidad extendida para restaurantes con operación intensa y automatización completa.",
    users: "20 usuarios",
    contacts: "Clientes ilimitados",
    bullets: [
      "Sub-agentes IA avanzados",
      "Límites operativos altos",
      "Preparado para escalar el negocio",
    ],
  },
];

export default function BillingPage() {
  const { data: tenant, isLoading } = useTenant();
  const checkout = useCreateBillingCheckout();
  const searchParams = useSearchParams();

  if (isLoading || !tenant) {
    return (
      <Group justify="center" py="xl">
        <Loader color="indigo" />
      </Group>
    );
  }

  const currentPlan = normalizeTenantPlan(tenant.plan);
  const success = searchParams.get("success") === "true";
  const cancelled = searchParams.get("cancel") === "true";

  function handleCheckout(plan: PaidPlan) {
    checkout.mutate(plan, {
      onSuccess: (response) => {
        window.location.assign(response.checkout_url);
      },
    });
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="Planes y Billing"
        subtitle="Gestiona tu plan del restaurante y activa upgrades seguros con Mercado Pago."
      />

      {(success || cancelled) && (
        <Alert
          color={success ? "green" : "yellow"}
          icon={success ? <IconCheck size={16} /> : <IconAlertCircle size={16} />}
          radius="md"
        >
          {success
            ? "Pago autorizado. El plan se actualizará en segundos cuando llegue la confirmación de Mercado Pago."
            : "El checkout fue cancelado. Tu plan actual no cambió."}
        </Alert>
      )}

      <SectionCard title="Estado actual">
        <Group justify="space-between" align="center" wrap="wrap" gap="md">
          <Group gap="sm">
            <Badge color="indigo" variant="light" size="lg">
              {currentPlan}
            </Badge>
            {tenant.stripe_subscription_id && (
              <Badge color="green" variant="light">
                Suscripción activa
              </Badge>
            )}
          </Group>
          <Stack gap={2} align="flex-end">
            <Text fw={600}>{tenant.nombre}</Text>
            <Text size="sm" c="dimmed">
              {tenant.max_users} usuarios · {tenant.max_leads_mes.toLocaleString("es-CL")}{" "}
              clientes/mes
            </Text>
          </Stack>
        </Group>
      </SectionCard>

      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
        {PLAN_CARDS.map((card) => {
          const isCurrent = currentPlan === card.plan;
          const isPaid = card.plan === TenantPlan.PLUS || card.plan === TenantPlan.PRO;
          const isUpgradeDisabled =
            checkout.isPending ||
            isCurrent ||
            !isPaid ||
            currentPlan === TenantPlan.PRO ||
            (currentPlan === TenantPlan.PLUS && card.plan === TenantPlan.PLUS);

          return (
            <Card key={card.plan} withBorder radius="lg" padding="lg">
              <Stack gap="md" h="100%">
                <Group justify="space-between" align="center">
                  <Group gap={6}>
                    <Badge color={card.badgeColor} variant="light">
                      {card.title}
                    </Badge>
                    {card.popular && (
                      <Badge color="orange" variant="filled" size="sm">
                        ★ Más popular
                      </Badge>
                    )}
                  </Group>
                  {isCurrent && (
                    <Badge color="green" variant="dot">
                      Actual
                    </Badge>
                  )}
                </Group>

                <Text fw={700} fz="xl">
                  {card.title}
                </Text>
                <Group gap={6} align="baseline">
                  <Text
                    style={{
                      fontFamily: TYPOGRAPHY.kpiNumber.fontFamily,
                      fontVariantNumeric: TYPOGRAPHY.kpiNumber.fontVariantNumeric,
                      fontSize: 34,
                      fontWeight: 700,
                      lineHeight: 1.1,
                    }}
                  >
                    {card.price}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {card.priceDetail}
                  </Text>
                </Group>
                <Text size="sm" c="dimmed">
                  {card.description}
                </Text>

                <Group gap="md">
                  <Group gap={6}>
                    <IconUsersGroup size={16} />
                    <Text size="sm">{card.users}</Text>
                  </Group>
                  <Group gap={6}>
                    <IconRocket size={16} />
                    <Text size="sm">{card.contacts}</Text>
                  </Group>
                </Group>

                <Stack gap={8} style={{ flex: 1 }}>
                  {card.bullets.map((bullet) => (
                    <Group key={bullet} gap={8} align="flex-start" wrap="nowrap">
                      <IconCheck
                        size={14}
                        style={{ marginTop: 3, flexShrink: 0 }}
                        color="var(--mantine-color-green-6)"
                      />
                      <Text size="sm">{bullet}</Text>
                    </Group>
                  ))}
                </Stack>

                {isPaid ? (
                  <Button
                    color={card.plan === TenantPlan.PRO ? "grape" : "blue"}
                    leftSection={<IconCreditCard size={16} />}
                    loading={checkout.isPending}
                    disabled={isUpgradeDisabled}
                    fullWidth
                    onClick={() => {
                      if (card.plan === TenantPlan.PLUS || card.plan === TenantPlan.PRO) {
                        handleCheckout(card.plan);
                      }
                    }}
                  >
                    {isCurrent ? "Plan actual" : `Subir a ${card.title}`}
                  </Button>
                ) : (
                  <Button variant="light" color="gray" disabled fullWidth>
                    Incluido al registrarte
                  </Button>
                )}
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>
    </Stack>
  );
}
