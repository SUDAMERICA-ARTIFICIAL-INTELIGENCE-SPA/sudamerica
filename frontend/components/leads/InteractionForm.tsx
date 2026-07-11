"use client";

import { useCreateInteraction } from "@/hooks/useLeadInteractions";
import { InteractionTipo } from "@/lib/enums";
import { Button, Group, Select, Stack, Textarea } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconPlus } from "@tabler/icons-react";

const TIPO_OPTIONS = Object.values(InteractionTipo).map((t) => ({
  value: t,
  label: t.charAt(0) + t.slice(1).toLowerCase(),
}));

interface InteractionFormProps {
  leadId: string;
}

interface FormValues {
  tipo: InteractionTipo;
  descripcion: string;
}

export function InteractionForm({ leadId }: InteractionFormProps) {
  const { mutate: create, isPending } = useCreateInteraction(leadId);

  const form = useForm<FormValues>({
    initialValues: {
      tipo: InteractionTipo.NOTA,
      descripcion: "",
    },
    validate: {
      descripcion: (v) => (v.trim().length < 3 ? "Descripción requerida" : null),
    },
  });

  function handleSubmit(values: FormValues) {
    create(values, {
      onSuccess: () => form.reset(),
    });
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="sm">
        <Group gap="sm" align="flex-start">
          <Select
            data={TIPO_OPTIONS}
            radius="md"
            size="sm"
            allowDeselect={false}
            style={{ width: 130, flexShrink: 0 }}
            aria-label="Tipo de interacción"
            {...form.getInputProps("tipo")}
          />
          <Textarea
            placeholder="¿Qué ocurrió? Ej: Llamada realizada, presenté propuesta…"
            radius="md"
            size="sm"
            minRows={2}
            autosize
            style={{ flex: 1 }}
            aria-label="Descripción de la interacción"
            {...form.getInputProps("descripcion")}
          />
        </Group>
        <Group justify="flex-end">
          <Button
            type="submit"
            size="xs"
            color="indigo"
            radius="md"
            leftSection={<IconPlus size={14} />}
            loading={isPending}
            aria-label="Registrar interacción"
          >
            Registrar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
