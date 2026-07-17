"use client";

import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useCreateSucursal, useSucursales, useUpdateSucursal } from "@/hooks/useSucursales";
import { useTenant } from "@/hooks/useTenant";
import { getTenantConfig } from "@/lib/onboarding";
import { type SectorField, getSectorConfig } from "@/lib/sector-config";
import type { Sucursal } from "@/lib/types";
import {
  Button,
  Divider,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { TimeInput } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { IconArrowLeft, IconArrowRight } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { type OnboardingStepProps, nowIso, useSaveOnboarding } from "./shared";

const MONEDA_OPTIONS = [
  { value: "CLP", label: "Peso chileno (CLP)" },
  { value: "ARS", label: "Peso argentino (ARS)" },
  { value: "PEN", label: "Sol peruano (PEN)" },
  { value: "COP", label: "Peso colombiano (COP)" },
  { value: "MXN", label: "Peso mexicano (MXN)" },
  { value: "UYU", label: "Peso uruguayo (UYU)" },
  { value: "PYG", label: "Guaraní (PYG)" },
  { value: "BOB", label: "Boliviano (BOB)" },
  { value: "USD", label: "Dólar (USD)" },
];

const TZ_OPTIONS = [
  "America/Santiago",
  "America/Argentina/Buenos_Aires",
  "America/Lima",
  "America/Bogota",
  "America/Mexico_City",
  "America/Montevideo",
  "America/Asuncion",
  "America/La_Paz",
].map((tz) => ({ value: tz, label: tz.split("/").slice(1).join("/").replace(/_/g, " ") }));

interface PerfilForm {
  direccion: string;
  telefono: string;
  ciudad: string;
  pais: string;
  zona_delivery: string;
  horario_dias: string;
  horario_apertura: string;
  horario_cierre: string;
  moneda: string;
  zona_horaria: string;
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Valor inicial de un campo de sector según su tipo, leyendo config previa si existe. */
function sectorInitial(
  field: SectorField,
  config: Record<string, unknown>,
): string | number | boolean {
  const prev = config[field.key];
  if (field.type === "boolean") return typeof prev === "boolean" ? prev : false;
  if (field.type === "number") return typeof prev === "number" ? prev : "";
  return typeof prev === "string" ? prev : "";
}

export function StepPerfil({ goNext, goBack }: OnboardingStepProps) {
  const { data: tenant } = useTenant();
  const { data: sucursales } = useSucursales();
  const rubro = useRubroLabels();
  const createSucursal = useCreateSucursal();
  const updateSucursal = useUpdateSucursal();
  const save = useSaveOnboarding();

  const config = getTenantConfig(tenant);
  const sectorFields = getSectorConfig(rubro.sector).fields;
  const principal = useMemo<Sucursal | undefined>(
    () => sucursales?.find((s) => s.es_principal) ?? sucursales?.[0],
    [sucursales],
  );

  const horarioPrev = (principal?.horario ?? {}) as Record<string, unknown>;
  const form = useForm<PerfilForm>({
    initialValues: {
      direccion: principal?.direccion ?? "",
      telefono: principal?.telefono ?? "",
      ciudad: principal?.ciudad ?? "",
      pais: principal?.pais ?? "CL",
      zona_delivery: principal?.zona_delivery ?? "",
      horario_dias: str(horarioPrev.dias),
      horario_apertura: str(horarioPrev.apertura),
      horario_cierre: str(horarioPrev.cierre),
      moneda: str(config.moneda) || "CLP",
      zona_horaria: str(config.zona_horaria) || "America/Santiago",
    },
    validate: {
      telefono: (v) => (v.trim().length < 6 ? "Ingresa un teléfono/WhatsApp válido" : null),
    },
  });

  const [sectorValues, setSectorValues] = useState<Record<string, string | number | boolean>>(() =>
    Object.fromEntries(sectorFields.map((f) => [f.key, sectorInitial(f, config)])),
  );

  const busy = createSucursal.isPending || updateSucursal.isPending || save.isPending;

  async function handleContinue(values: PerfilForm) {
    const horario: Record<string, string> = {};
    if (values.horario_dias.trim()) horario.dias = values.horario_dias.trim();
    if (values.horario_apertura) horario.apertura = values.horario_apertura;
    if (values.horario_cierre) horario.cierre = values.horario_cierre;

    const sucursalBody = {
      direccion: values.direccion.trim() || null,
      telefono: values.telefono.trim() || null,
      zona_delivery: values.zona_delivery.trim() || null,
      ciudad: values.ciudad.trim() || null,
      pais: values.pais.trim() || "CL",
      horario: Object.keys(horario).length ? horario : null,
    };

    // Crea la sucursal principal si aún no existe (register no la crea); si ya existe, actualiza.
    if (principal) {
      await updateSucursal.mutateAsync({ id: principal.id, ...sucursalBody });
    } else {
      await createSucursal.mutateAsync({
        nombre: tenant?.nombre ?? "Sucursal principal",
        ...sucursalBody,
      });
    }

    // Campos de sector + transversales (moneda/zona horaria) → tenants.config.
    await save.mutateAsync({
      config: {
        moneda: values.moneda,
        zona_horaria: values.zona_horaria,
        ...sectorValues,
      },
      onboarding: { perfil_completed_at: nowIso() },
    });

    goNext();
  }

  return (
    <form onSubmit={form.onSubmit(handleContinue)}>
      <Stack gap="md">
        <Text c="dimmed" size="sm">
          Datos de tu {rubro.labels.recurso?.toLowerCase() ?? "local"}: solo lo que el agente y la
          ficha del negocio realmente usan.
        </Text>

        <TextInput
          label="Dirección"
          placeholder="Calle, número, comuna"
          {...form.getInputProps("direccion")}
        />
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <TextInput
            label="Teléfono / WhatsApp"
            placeholder="+56 9 ..."
            withAsterisk
            {...form.getInputProps("telefono")}
          />
          <TextInput label="Ciudad" {...form.getInputProps("ciudad")} />
        </SimpleGrid>

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <TextInput
            label="Días de atención"
            placeholder="Lun a Vie"
            {...form.getInputProps("horario_dias")}
          />
          <TimeInput label="Abre" {...form.getInputProps("horario_apertura")} />
          <TimeInput label="Cierra" {...form.getInputProps("horario_cierre")} />
        </SimpleGrid>

        <Textarea
          label="Zona de cobertura / delivery"
          placeholder="Retiro en local, 5 km a la redonda, toda la ciudad…"
          autosize
          minRows={2}
          {...form.getInputProps("zona_delivery")}
        />

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <Select label="Moneda" data={MONEDA_OPTIONS} {...form.getInputProps("moneda")} />
          <Select
            label="Zona horaria"
            data={TZ_OPTIONS}
            searchable
            {...form.getInputProps("zona_horaria")}
          />
        </SimpleGrid>

        {sectorFields.length > 0 && (
          <>
            <Divider label="Datos de tu rubro" labelPosition="left" />
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              {sectorFields.map((field) => (
                <SectorFieldInput
                  key={field.key}
                  field={field}
                  value={sectorValues[field.key] ?? ""}
                  onChange={(value) =>
                    setSectorValues((current) => ({ ...current, [field.key]: value }))
                  }
                />
              ))}
            </SimpleGrid>
          </>
        )}

        <Group justify="space-between" mt="xs">
          <Button
            variant="subtle"
            color="gray"
            leftSection={<IconArrowLeft size={16} />}
            onClick={goBack}
          >
            Atrás
          </Button>
          <Button type="submit" loading={busy} rightSection={<IconArrowRight size={16} />}>
            Guardar y continuar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}

function SectorFieldInput({
  field,
  value,
  onChange,
}: {
  field: SectorField;
  value: string | number | boolean;
  onChange: (value: string | number | boolean) => void;
}) {
  if (field.type === "boolean") {
    return (
      <Switch
        label={field.label}
        checked={Boolean(value)}
        onChange={(event) => onChange(event.currentTarget.checked)}
        mt="md"
      />
    );
  }
  if (field.type === "number") {
    return (
      <NumberInput
        label={field.label}
        value={typeof value === "number" ? value : ""}
        onChange={(val) => onChange(typeof val === "number" ? val : "")}
      />
    );
  }
  if (field.type === "select") {
    return (
      <Select
        label={field.label}
        data={[...(field.options ?? [])]}
        value={typeof value === "string" ? value : ""}
        onChange={(val) => onChange(val ?? "")}
        clearable
      />
    );
  }
  return (
    <TextInput
      label={field.label}
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onChange(event.currentTarget.value)}
    />
  );
}
