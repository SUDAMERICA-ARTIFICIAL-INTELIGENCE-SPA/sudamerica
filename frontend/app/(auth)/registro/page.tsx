"use client";

import { useTenant } from "@/hooks/useTenant";
import { useAuth } from "@/lib/auth";
import { OnboardingStep, getTenantOnboardingState, resolveOnboardingStep } from "@/lib/onboarding";
import { ACCENT, DARK, GLASS, SHADOWS_DARK } from "@/lib/theme-tokens";
import { Box, Center, Loader, Paper, Stepper, Text, Title } from "@mantine/core";
import {
  IconApps,
  IconBrandWhatsapp,
  IconBuildingStore,
  IconCategory2,
  IconUpload,
  IconUserPlus,
} from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { StepCuenta } from "./steps/StepCuenta";
import { StepDatos } from "./steps/StepDatos";
import { StepListo } from "./steps/StepListo";
import { StepModulos } from "./steps/StepModulos";
import { StepPerfil } from "./steps/StepPerfil";
import { StepRubro } from "./steps/StepRubro";
import { StepWhatsApp } from "./steps/StepWhatsApp";
import { withAlpha } from "./steps/shared";

const STEP_META = [
  { label: "Cuenta", description: "Tu negocio", icon: IconUserPlus },
  { label: "Rubro", description: "Qué haces", icon: IconCategory2 },
  { label: "Perfil", description: "Datos base", icon: IconBuildingStore },
  { label: "Módulos", description: "Tu operación", icon: IconApps },
  { label: "Datos", description: "Catálogo", icon: IconUpload },
  { label: "WhatsApp", description: "Conectar", icon: IconBrandWhatsapp },
] as const;

export default function OnboardingPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: tenant, isLoading: tenantLoading } = useTenant();
  const [active, setActive] = useState<number>(OnboardingStep.Cuenta);
  const initializedRef = useRef(false);

  // Hidratación del paso activo: pre-auth siempre Cuenta; autenticado, el primer paso no
  // resuelto según `config.onboarding`. Al registrarse, isAuthenticated pasa a true y el
  // efecto vuelve a correr resolviendo a Rubro (paso 1). Ver resolveOnboardingStep.
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      setActive(OnboardingStep.Cuenta);
      initializedRef.current = false;
      return;
    }
    if (tenantLoading || !tenant) return;
    if (initializedRef.current) return;
    setActive(resolveOnboardingStep(getTenantOnboardingState(tenant), true));
    initializedRef.current = true;
  }, [authLoading, isAuthenticated, tenantLoading, tenant]);

  const goNext = () => setActive((step) => Math.min(step + 1, OnboardingStep.Listo));
  const goBack = () => setActive((step) => Math.max(step - 1, OnboardingStep.Cuenta));

  const loading = authLoading || (isAuthenticated && tenantLoading && !tenant);

  return (
    <Box
      style={{
        minHeight: "100vh",
        padding: "40px 16px",
        background: `radial-gradient(circle at 50% -10%, ${withAlpha(ACCENT, 0.22)}, transparent 45%), linear-gradient(160deg, ${DARK.background} 0%, ${DARK.surface} 55%, ${DARK.background} 100%)`,
      }}
    >
      <Paper
        maw={780}
        mx="auto"
        radius="xl"
        p={0}
        style={{
          overflow: "hidden",
          background: GLASS.dark.background,
          backdropFilter: GLASS.dark.backdropFilter,
          border: `1px solid ${DARK.hairline}`,
          boxShadow: SHADOWS_DARK.xl,
        }}
      >
        {/* Barra de acento con el gradiente de marca (coral/amber/ocean/teal). */}
        <Box style={{ height: 4, background: "var(--sudamerica-gradient)" }} />

        <Box p={{ base: "lg", sm: "xl" }}>
          <Title order={2} c="white" mb={4}>
            Configura tu negocio
          </Title>
          <Text c={withAlpha("#FFFFFF", 0.6)} mb="xl">
            Unos pocos pasos y tu agente de WhatsApp queda listo para atender.
          </Text>

          <Stepper
            active={active}
            color="indigo"
            size="sm"
            iconSize={34}
            mb="xl"
            styles={{
              separator: { marginInline: 4 },
              stepDescription: { fontSize: 11 },
            }}
          >
            {STEP_META.map((meta) => (
              <Stepper.Step
                key={meta.label}
                label={meta.label}
                description={meta.description}
                icon={<meta.icon size={18} />}
              />
            ))}
          </Stepper>

          {loading ? (
            <Center mih={280}>
              <Loader color="indigo" />
            </Center>
          ) : (
            <StepBody active={active} goNext={goNext} goBack={goBack} />
          )}
        </Box>
      </Paper>
    </Box>
  );
}

function StepBody({
  active,
  goNext,
  goBack,
}: {
  active: number;
  goNext: () => void;
  goBack: () => void;
}) {
  switch (active) {
    case OnboardingStep.Cuenta:
      return <StepCuenta goNext={goNext} goBack={goBack} />;
    case OnboardingStep.Rubro:
      return <StepRubro goNext={goNext} goBack={goBack} />;
    case OnboardingStep.Perfil:
      return <StepPerfil goNext={goNext} goBack={goBack} />;
    case OnboardingStep.Modulos:
      return <StepModulos goNext={goNext} goBack={goBack} />;
    case OnboardingStep.Datos:
      return <StepDatos goNext={goNext} goBack={goBack} />;
    case OnboardingStep.WhatsApp:
      return <StepWhatsApp goNext={goNext} goBack={goBack} />;
    default:
      return <StepListo goNext={goNext} goBack={goBack} />;
  }
}
