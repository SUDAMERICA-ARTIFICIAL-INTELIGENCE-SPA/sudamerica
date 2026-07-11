"use client";

import { MenuImportModal } from "@/components/carta/MenuImportModal";
import { AIAgentSettings } from "@/components/configuracion/AIAgentSettings";
import { QRModal } from "@/components/prospectos/QRModal";
import { useAgenteConfigRaw, useUpdateAgentProfile } from "@/hooks/useAgenteConfig";
import { useProductos } from "@/hooks/useProductos";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useTenant, useUpdateTenant } from "@/hooks/useTenant";
import { useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import { useAuth } from "@/lib/auth";
import {
  type TenantOnboardingState,
  getTenantConfig,
  getTenantOnboardingState,
  needsTenantOnboarding,
  normalizeTenantPlan,
} from "@/lib/onboarding";
import { RUBRO_DEFAULT, getRubroDef, plural, resolveRubro } from "@/lib/rubros";
import { DARK, LIGHT, SEMANTIC, SHADOWS_DARK } from "@/lib/theme-tokens";
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Group,
  Loader,
  MantineProvider,
  Paper,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconArrowRight,
  IconBox,
  IconBrandWhatsapp,
  IconBuildingStore,
  IconCheck,
  IconChefHat,
  IconCreditCard,
  IconQrcode,
  IconRobot,
  IconToolsKitchen2,
} from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/** Convierte un color del design system (#RRGGBB) a rgba con alpha custom — evita hex sueltos. */
function withAlpha(hex: string, alpha: number): string {
  const r = Number.parseInt(hex.slice(1, 3), 16);
  const g = Number.parseInt(hex.slice(3, 5), 16);
  const b = Number.parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

interface BusinessFormState {
  nombre: string;
  tipo_comida: string;
  horario_atencion: string;
  zona_delivery: string;
  descripcion_negocio: string;
}

function hasStepState(
  onboarding: TenantOnboardingState,
  completedKey: keyof TenantOnboardingState,
  skippedKey?: keyof TenantOnboardingState,
): boolean {
  return Boolean(onboarding[completedKey] || (skippedKey ? onboarding[skippedKey] : undefined));
}

function resolveInitialStep(onboarding: TenantOnboardingState): number {
  if (!hasStepState(onboarding, "business_completed_at")) return 0;
  if (!hasStepState(onboarding, "menu_completed_at", "menu_skipped_at")) return 1;
  if (!hasStepState(onboarding, "ai_completed_at", "ai_skipped_at")) return 2;
  if (!hasStepState(onboarding, "whatsapp_completed_at", "whatsapp_skipped_at")) return 3;
  return 4;
}

function readConfigString(config: Record<string, unknown>, key: string): string {
  const value = config[key];
  return typeof value === "string" ? value : "";
}

function buildDefaultPersonality(config: Record<string, unknown>): string {
  const tono = readConfigString(config, "tono") || "mixto";
  const tipoComida = readConfigString(config, "tipo_comida") || "la carta";
  return `Habla en tono ${tono}, responde en español y guía pedidos de ${tipoComida} con rapidez y claridad.`;
}

function onboardingTimestamp(field: keyof TenantOnboardingState): Record<string, string> {
  return { [field]: new Date().toISOString() };
}

export default function OnboardingPage() {
  const router = useRouter();
  const initializedRef = useRef(false);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: tenant, isLoading: tenantLoading } = useTenant();
  const updateTenant = useUpdateTenant();
  const { data: rawAgentConfig, isLoading: agentLoading } = useAgenteConfigRaw();
  const updateAgentProfile = useUpdateAgentProfile();
  const { data: productosData, isLoading: productsLoading } = useProductos({
    page: 1,
    page_size: 1,
  });
  const { data: whatsappData, isLoading: whatsappLoading } = useWhatsAppStatus({
    enabled: isAuthenticated,
    refetchInterval: 3000,
  });
  const rubro = useRubroLabels();

  const [menuOpened, menuHandlers] = useDisclosure(false);
  const [qrOpened, qrHandlers] = useDisclosure(false);
  const [active, setActive] = useState(0);
  const [business, setBusiness] = useState<BusinessFormState>({
    nombre: "",
    tipo_comida: "",
    horario_atencion: "",
    zona_delivery: "",
    descripcion_negocio: "",
  });
  const [agentName, setAgentName] = useState("");
  const [personality, setPersonality] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!tenant || initializedRef.current) return;

    const config = getTenantConfig(tenant);
    const onboarding = getTenantOnboardingState(tenant);
    setBusiness({
      nombre: tenant.nombre,
      tipo_comida: readConfigString(config, "tipo_comida"),
      horario_atencion: readConfigString(config, "horario_atencion"),
      zona_delivery: readConfigString(config, "zona_delivery"),
      descripcion_negocio: readConfigString(config, "descripcion_negocio"),
    });
    setActive(resolveInitialStep(onboarding));
    initializedRef.current = true;
  }, [tenant]);

  useEffect(() => {
    if (!tenant) return;
    const config = getTenantConfig(tenant);
    if (!agentName) {
      setAgentName(
        typeof rawAgentConfig?.nombre_agente === "string" && rawAgentConfig.nombre_agente
          ? rawAgentConfig.nombre_agente
          : `${tenant.nombre} IA`,
      );
    }
    if (!personality) {
      setPersonality(
        typeof rawAgentConfig?.personalidad === "string" && rawAgentConfig.personalidad
          ? rawAgentConfig.personalidad
          : buildDefaultPersonality(config),
      );
    }
  }, [agentName, personality, rawAgentConfig, tenant]);

  if (authLoading || tenantLoading || !tenant) {
    return (
      <Center mih="100vh">
        <Loader color="indigo" />
      </Center>
    );
  }

  const tenantConfig = getTenantConfig(tenant);
  const currentPlan = normalizeTenantPlan(tenant.plan);
  const menuReady = (productosData?.meta.total ?? 0) > 0;
  const whatsappReady = whatsappData?.status === "open";
  const requiresOnboarding = needsTenantOnboarding(tenant);

  // Rubro del tenant ya se conoce en este punto del flujo (tenant cargado arriba) — byte-identidad
  // para restaurante (copy/íconos sin cambios), genérico para el resto (ver useRubroLabels).
  const isDefault = rubro.key === RUBRO_DEFAULT;
  const isGastro = rubro.sector === "gastronomia";
  const catalogoLabel = rubro.labels.catalogo;
  const catalogoLower = catalogoLabel.toLowerCase();
  const itemsPluralLower = plural(rubro.labels.item).toLowerCase();

  async function saveBusinessStep() {
    const sector = getRubroDef(resolveRubro(tenantConfig)).sector;
    await updateTenant.mutateAsync({
      nombre: business.nombre.trim(),
      config: {
        ...(typeof tenantConfig.rubro === "string" ? { rubro: tenantConfig.rubro } : {}),
        sector,
        tipo_comida: business.tipo_comida.trim(),
        horario_atencion: business.horario_atencion.trim(),
        zona_delivery: business.zona_delivery.trim(),
        descripcion_negocio: business.descripcion_negocio.trim(),
        onboarding: {
          required: true,
          ...onboardingTimestamp("business_completed_at"),
        },
      },
    });
    setActive(1);
  }

  async function saveMenuStep(skipped = false) {
    await updateTenant.mutateAsync({
      config: {
        onboarding: {
          required: true,
          ...(skipped
            ? onboardingTimestamp("menu_skipped_at")
            : onboardingTimestamp("menu_completed_at")),
        },
      },
    });
    setActive(2);
  }

  async function saveAgentStep(skipped = false) {
    if (!skipped) {
      await updateAgentProfile.mutateAsync({
        nombre_agente: agentName.trim(),
        personalidad: personality.trim(),
      });
    }
    await updateTenant.mutateAsync({
      config: {
        onboarding: {
          required: true,
          ...(skipped
            ? onboardingTimestamp("ai_skipped_at")
            : onboardingTimestamp("ai_completed_at")),
        },
      },
    });
    setActive(3);
  }

  async function saveWhatsAppStep(skipped = false) {
    await updateTenant.mutateAsync({
      config: {
        onboarding: {
          required: false,
          completed_at: new Date().toISOString(),
          ...(skipped
            ? onboardingTimestamp("whatsapp_skipped_at")
            : onboardingTimestamp("whatsapp_completed_at")),
        },
      },
    });
    setActive(4);
  }

  return (
    <>
      <MenuImportModal opened={menuOpened} onClose={menuHandlers.close} />
      <QRModal opened={qrOpened} onClose={qrHandlers.close} />

      <Box
        style={{
          minHeight: "100vh",
          padding: "32px 16px",
          background: `radial-gradient(circle at top left, ${withAlpha(SEMANTIC.danger, 0.18)}, transparent 35%), linear-gradient(145deg, ${DARK.background} 0%, ${DARK.surface} 46%, ${DARK.background} 100%)`,
        }}
      >
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" maw={1180} mx="auto">
          <Paper
            radius="xl"
            p="xl"
            style={{
              background: `linear-gradient(180deg, ${withAlpha(LIGHT.surface, 0.06)} 0%, ${withAlpha(LIGHT.surface, 0.03)} 100%)`,
              border: `1px solid ${withAlpha(LIGHT.surface, 0.08)}`,
            }}
          >
            <Stack gap="lg">
              <Badge color="amber" variant="light" style={{ alignSelf: "flex-start" }}>
                Onboarding Comercial
              </Badge>
              <Stack gap={6}>
                <Title order={1} c="white">
                  {isDefault
                    ? "Deja el restaurante listo para operar hoy."
                    : "Deja tu negocio listo para operar hoy."}
                </Title>
                <Text c={withAlpha(LIGHT.surface, 0.72)} size="lg">
                  {isDefault
                    ? "El flujo conecta lo que ya existe en producción: carta, IA y WhatsApp, sin dejar pasos sueltos para el dueño."
                    : `El flujo conecta lo que ya existe en producción: ${catalogoLower}, IA y WhatsApp, sin dejar pasos sueltos para el dueño.`}
                </Text>
              </Stack>

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                {[
                  {
                    icon: isGastro ? <IconChefHat size={18} /> : <IconBuildingStore size={18} />,
                    title: "Plan actual",
                    text: currentPlan,
                  },
                  {
                    icon: isGastro ? <IconToolsKitchen2 size={18} /> : <IconBox size={18} />,
                    title: isDefault ? "Carta cargada" : catalogoLabel,
                    text: menuReady ? "Sí" : "Pendiente",
                  },
                  {
                    icon: <IconRobot size={18} />,
                    title: "Perfil IA",
                    text: agentLoading ? "Cargando..." : agentName || "Pendiente",
                  },
                  {
                    icon: <IconBrandWhatsapp size={18} />,
                    title: "WhatsApp",
                    text: whatsappReady ? "Conectado" : "Pendiente",
                  },
                ].map((item) => (
                  <Card key={item.title} withBorder radius="lg" padding="md">
                    <Group align="flex-start" wrap="nowrap">
                      <ThemeIcon color="indigo" variant="light" radius="md">
                        {item.icon}
                      </ThemeIcon>
                      <Stack gap={2}>
                        <Text size="xs" tt="uppercase" fw={700} c="dimmed">
                          {item.title}
                        </Text>
                        <Text fw={600}>{item.text}</Text>
                      </Stack>
                    </Group>
                  </Card>
                ))}
              </SimpleGrid>

              <Alert color={requiresOnboarding ? "blue" : "green"} radius="lg">
                {requiresOnboarding
                  ? "Este tenant seguirá entrando al wizard hasta completar o saltar los pasos clave."
                  : "El wizard ya quedó cerrado para este tenant. Puedes volver a Billing o al dashboard cuando quieras."}
              </Alert>
            </Stack>
          </Paper>

          <MantineProvider forceColorScheme="light">
            <Paper
              radius="xl"
              p="xl"
              style={{
                background: LIGHT.surface,
                boxShadow: SHADOWS_DARK.lg,
              }}
            >
              <Stack gap="lg">
                <Stack gap={4}>
                  <Title order={2}>Wizard de activación</Title>
                  <Text c="dimmed">
                    {isDefault
                      ? "Revisa negocio, sube la carta, ajusta la IA y conecta WhatsApp."
                      : `Revisa negocio, actualiza ${catalogoLower}, ajusta la IA y conecta WhatsApp.`}
                  </Text>
                </Stack>

                <Stepper active={active} color="indigo" radius="md">
                  <Stepper.Step label="Negocio" description="Datos base" />
                  <Stepper.Step
                    label={isDefault ? "Carta" : catalogoLabel}
                    description={isDefault ? "Menú" : "Catálogo"}
                  />
                  <Stepper.Step label="IA" description="Perfil" />
                  <Stepper.Step label="WhatsApp" description="QR" />
                  <Stepper.Completed>
                    <Stack gap="lg">
                      <ThemeIcon color="green" size={72} radius="xl" variant="light">
                        <IconCheck size={36} />
                      </ThemeIcon>
                      <Stack gap={4}>
                        <Title order={3}>Restaurante activado</Title>
                        <Text c="dimmed">
                          Ya puedes operar desde el dashboard y, si quieres monetizar de inmediato,
                          ir a billing para subir de plan.
                        </Text>
                      </Stack>
                      <Group>
                        <Button
                          color="grape"
                          leftSection={<IconCreditCard size={16} />}
                          onClick={() => router.push("/billing")}
                        >
                          Ver planes
                        </Button>
                        <Button
                          variant="light"
                          rightSection={<IconArrowRight size={16} />}
                          onClick={() => router.push("/dashboard")}
                        >
                          Ir al dashboard
                        </Button>
                      </Group>
                    </Stack>
                  </Stepper.Completed>
                </Stepper>

                {active === 0 && (
                  <Stack gap="md">
                    <TextInput
                      label="Nombre del restaurante"
                      value={business.nombre}
                      onChange={(event) =>
                        setBusiness((current) => ({
                          ...current,
                          nombre: event.currentTarget.value,
                        }))
                      }
                    />
                    <TextInput
                      label="Tipo de comida"
                      placeholder="Pizzas, sushi, hamburguesas..."
                      value={business.tipo_comida}
                      onChange={(event) =>
                        setBusiness((current) => ({
                          ...current,
                          tipo_comida: event.currentTarget.value,
                        }))
                      }
                    />
                    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                      <TextInput
                        label="Horario de atención"
                        placeholder="11:00 a 23:00"
                        value={business.horario_atencion}
                        onChange={(event) =>
                          setBusiness((current) => ({
                            ...current,
                            horario_atencion: event.currentTarget.value,
                          }))
                        }
                      />
                      <TextInput
                        label="Zona de delivery"
                        placeholder="10 km, retiro en local, toda la ciudad..."
                        value={business.zona_delivery}
                        onChange={(event) =>
                          setBusiness((current) => ({
                            ...current,
                            zona_delivery: event.currentTarget.value,
                          }))
                        }
                      />
                    </SimpleGrid>
                    <Textarea
                      label="Qué hace especial al restaurante"
                      minRows={4}
                      autosize
                      value={business.descripcion_negocio}
                      onChange={(event) =>
                        setBusiness((current) => ({
                          ...current,
                          descripcion_negocio: event.currentTarget.value,
                        }))
                      }
                    />
                    <Group justify="space-between">
                      <Badge variant="light" color="gray">
                        Tono IA sugerido: {readConfigString(tenantConfig, "tono") || "mixto"}
                      </Badge>
                      <Button
                        onClick={() => void saveBusinessStep()}
                        loading={updateTenant.isPending}
                        disabled={
                          !business.nombre.trim() ||
                          !business.tipo_comida.trim() ||
                          !business.horario_atencion.trim() ||
                          !business.zona_delivery.trim()
                        }
                      >
                        Guardar y continuar
                      </Button>
                    </Group>
                  </Stack>
                )}

                {active === 1 && (
                  <Stack gap="md">
                    <Alert color={menuReady ? "green" : "blue"} radius="md">
                      {productsLoading
                        ? isDefault
                          ? "Cargando estado de la carta..."
                          : `Cargando estado de ${catalogoLower}...`
                        : menuReady
                          ? isDefault
                            ? `Carta detectada con ${productosData?.meta.total ?? 0} platos activos.`
                            : `${catalogoLabel} con ${productosData?.meta.total ?? 0} ${itemsPluralLower} disponibles.`
                          : isDefault
                            ? "Aún no hay platos cargados. Usa el importador para subir PDF, imagen o URL."
                            : `Aún no hay ${itemsPluralLower} disponibles. Usa el importador para subir PDF, imagen o URL.`}
                    </Alert>
                    <Group>
                      <Button
                        leftSection={
                          isGastro ? <IconToolsKitchen2 size={16} /> : <IconBox size={16} />
                        }
                        onClick={menuHandlers.open}
                      >
                        {isDefault ? "Abrir importador de carta" : rubro.labels.ingesta}
                      </Button>
                      <Button variant="light" onClick={() => router.push("/carta")}>
                        {isDefault ? "Ver carta actual" : `Ver ${catalogoLabel}`}
                      </Button>
                    </Group>
                    <Group justify="space-between">
                      <Button variant="subtle" color="gray" onClick={() => void saveMenuStep(true)}>
                        Lo haré luego
                      </Button>
                      <Button onClick={() => void saveMenuStep(false)} disabled={!menuReady}>
                        {isDefault
                          ? "Continuar con la carta cargada"
                          : `Continuar con ${catalogoLabel}`}
                      </Button>
                    </Group>
                  </Stack>
                )}

                {active === 2 && (
                  <Stack gap="md">
                    <TextInput
                      label="Nombre visible del agente"
                      value={agentName}
                      onChange={(event) => setAgentName(event.currentTarget.value)}
                    />
                    <Textarea
                      label="Personalidad e instrucciones"
                      minRows={4}
                      autosize
                      value={personality}
                      onChange={(event) => setPersonality(event.currentTarget.value)}
                    />
                    <AIAgentSettings />
                    <Group justify="space-between">
                      <Button
                        variant="subtle"
                        color="gray"
                        onClick={() => void saveAgentStep(true)}
                      >
                        Usar defaults
                      </Button>
                      <Button
                        onClick={() => void saveAgentStep(false)}
                        loading={updateAgentProfile.isPending || updateTenant.isPending}
                        disabled={!agentName.trim() || !personality.trim()}
                      >
                        Guardar IA y continuar
                      </Button>
                    </Group>
                  </Stack>
                )}

                {active === 3 && (
                  <Stack gap="md">
                    <Alert color={whatsappReady ? "green" : "blue"} radius="md">
                      {whatsappLoading
                        ? "Revisando estado de WhatsApp..."
                        : whatsappReady
                          ? "WhatsApp ya está conectado y el agente puede recibir pedidos."
                          : "Todavía no hay una instancia conectada. Abre el flujo QR para vincular el número del restaurante."}
                    </Alert>
                    <Group>
                      <Button
                        leftSection={<IconQrcode size={16} />}
                        color="green"
                        onClick={qrHandlers.open}
                      >
                        Conectar por QR
                      </Button>
                      <Button variant="light" onClick={() => router.push("/prospectos")}>
                        Ir a conversaciones IA
                      </Button>
                    </Group>
                    <Group justify="space-between">
                      <Button
                        variant="subtle"
                        color="gray"
                        onClick={() => void saveWhatsAppStep(true)}
                      >
                        Lo conectaré después
                      </Button>
                      <Button
                        color="green"
                        onClick={() => void saveWhatsAppStep(false)}
                        disabled={!whatsappReady}
                      >
                        Finalizar onboarding
                      </Button>
                    </Group>
                  </Stack>
                )}
              </Stack>
            </Paper>
          </MantineProvider>
        </SimpleGrid>
      </Box>
    </>
  );
}
