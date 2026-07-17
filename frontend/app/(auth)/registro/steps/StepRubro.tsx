"use client";

import { useRubroLabels } from "@/hooks/useRubroLabels";
import { CAPACIDADES_META } from "@/lib/capacidades";
import { construirSidebarCanonico } from "@/lib/nav-canonico";
import { RUBROS, RUBRO_OPTIONS, type RubroKey, getRubroDef, rubroSectorConfig } from "@/lib/rubros";
import { SECTOR_OPTIONS } from "@/lib/sector-config";
import { ACCENT } from "@/lib/theme-tokens";
import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  Select,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { IconArrowLeft, IconArrowRight, IconSparkles } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { type OnboardingStepProps, nowIso, useSaveOnboarding, withAlpha } from "./shared";

/** Opciones agrupadas por sector para el Select, con emoji en la etiqueta. */
const GROUPED_OPTIONS = SECTOR_OPTIONS.map((sector) => ({
  group: sector.label,
  items: RUBRO_OPTIONS.filter((option) => RUBROS[option.value].sector === sector.value).map(
    (option) => ({ value: option.value, label: `${option.emoji}  ${option.label}` }),
  ),
})).filter((groupData) => groupData.items.length > 0);

/** Primitivas que mejor comunican el renombrado por rubro. */
const RENAME_PRIMITIVES = ["catalogo", "item", "orden", "agenda", "parte"] as const;

export function StepRubro({ goNext, goBack }: OnboardingStepProps) {
  const currentRubro = useRubroLabels();
  const save = useSaveOnboarding();
  const [selected, setSelected] = useState<RubroKey>(currentRubro.key);

  const def = useMemo(() => getRubroDef(selected), [selected]);
  const sectorLabel = rubroSectorConfig(def.key).label;
  const modules = useMemo(() => construirSidebarCanonico(def), [def]);

  async function handleContinue() {
    await save.mutateAsync({
      config: { rubro: def.key, sector: def.sector },
      onboarding: { rubro_completed_at: nowIso() },
      successMessage: `Rubro: ${def.nombre}`,
    });
    goNext();
  }

  return (
    <Stack gap="lg">
      <Text c="dimmed" size="sm">
        ¿A qué se dedica tu negocio? Busca tu rubro: adaptamos los módulos, los nombres y el agente
        a tu operación.
      </Text>

      <Select
        label="Tu rubro"
        placeholder="Escribe lo que haces: peluquería, ferretería, veterinaria…"
        data={GROUPED_OPTIONS}
        value={selected}
        onChange={(value) => value && setSelected(value as RubroKey)}
        searchable
        nothingFoundMessage="Sin coincidencias — prueba otra palabra"
        maxDropdownHeight={280}
        withAsterisk
      />

      {/* Panel "qué cambia" en vivo para el rubro elegido. */}
      <Card
        radius="lg"
        p="lg"
        style={{
          background: withAlpha(ACCENT, 0.06),
          border: `1px solid ${withAlpha(ACCENT, 0.25)}`,
        }}
      >
        <Stack gap="md">
          <Group gap="sm" wrap="nowrap">
            <Text fz={34} lh={1}>
              {def.emoji}
            </Text>
            <Box>
              <Text fw={700} size="lg">
                {def.nombre}
              </Text>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                {sectorLabel}
              </Text>
            </Box>
          </Group>

          <Box>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb={6}>
              Cómo llamaremos las cosas
            </Text>
            <Group gap="xs">
              {RENAME_PRIMITIVES.map((primitiva) => (
                <Badge key={primitiva} variant="light" color="indigo" radius="sm">
                  {def.labels[primitiva]}
                </Badge>
              ))}
              {def.subEntidadLabel ? (
                <Badge variant="outline" color="grape" radius="sm">
                  {def.subEntidadLabel}
                </Badge>
              ) : null}
            </Group>
          </Box>

          <Box>
            <Group gap={6} mb={6}>
              <ThemeIcon size="sm" variant="light" color="indigo" radius="sm">
                <IconSparkles size={12} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Módulos que se activan ({def.capacidades.length})
              </Text>
            </Group>
            <Group gap="xs">
              {def.capacidades.map((cap) => (
                <Tooltip
                  key={cap}
                  label={CAPACIDADES_META[cap].descripcion}
                  multiline
                  w={220}
                  withArrow
                >
                  <Badge variant="dot" color="teal" radius="sm" style={{ cursor: "help" }}>
                    {CAPACIDADES_META[cap].label}
                  </Badge>
                </Tooltip>
              ))}
            </Group>
            <Text size="xs" c="dimmed" mt={8}>
              Tu panel tendrá {modules.length} secciones adaptadas a {def.nombre.toLowerCase()}.
            </Text>
          </Box>
        </Stack>
      </Card>

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
          Confirmar rubro
        </Button>
      </Group>
    </Stack>
  );
}
