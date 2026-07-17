"use client";

import { useRubroLabels } from "@/hooks/useRubroLabels";
import { construirSidebarCanonico, navLabelCanonico } from "@/lib/nav-canonico";
import { Anchor, Badge, Button, Card, Group, SimpleGrid, Stack, Text } from "@mantine/core";
import { IconArrowLeft, IconArrowRight, IconExternalLink } from "@tabler/icons-react";
import { useMemo } from "react";
import { type OnboardingStepProps, nowIso, useSaveOnboarding } from "./shared";

export function StepModulos({ goNext, goBack }: OnboardingStepProps) {
  const rubro = useRubroLabels();
  const save = useSaveOnboarding();
  const categorias = useMemo(() => construirSidebarCanonico(rubro), [rubro]);

  async function handleContinue() {
    await save.mutateAsync({ onboarding: { capacidades_reviewed_at: nowIso() } });
    goNext();
  }

  return (
    <Stack gap="lg">
      <Text c="dimmed" size="sm">
        Según tu rubro ({rubro.emoji} {rubro.nombre}), tu panel se arma con estas secciones. Puedes
        ajustarlas más adelante en{" "}
        <Anchor href="/cuenta/modulos" size="sm">
          Cuenta → Módulos <IconExternalLink size={11} style={{ verticalAlign: "middle" }} />
        </Anchor>
        .
      </Text>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {categorias.map((categoria) => (
          <Card key={categoria.id} withBorder radius="lg" padding="md">
            <Group gap="xs" mb="xs" wrap="nowrap">
              <Badge
                variant="light"
                radius="sm"
                styles={{ root: { background: `${categoria.color}22`, color: categoria.color } }}
              >
                {categoria.num}
              </Badge>
              <Text fw={600}>{categoria.label}</Text>
            </Group>
            <Group gap={6}>
              {categoria.subs.map((sub) => (
                <Badge key={sub.id} variant="default" radius="sm" size="sm">
                  {navLabelCanonico(sub, rubro)}
                </Badge>
              ))}
            </Group>
          </Card>
        ))}
      </SimpleGrid>

      <Group justify="space-between">
        <Button
          variant="subtle"
          color="gray"
          leftSection={<IconArrowLeft size={16} />}
          onClick={goBack}
        >
          Atrás
        </Button>
        <Button
          onClick={() => void handleContinue()}
          loading={save.isPending}
          rightSection={<IconArrowRight size={16} />}
        >
          Se ve bien, continuar
        </Button>
      </Group>
    </Stack>
  );
}
