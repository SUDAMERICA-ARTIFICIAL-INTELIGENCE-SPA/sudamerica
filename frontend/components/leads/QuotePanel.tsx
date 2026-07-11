"use client";

import { useCreateQuote, useQuotes, useUpdateQuote } from "@/hooks/useQuotes";
import { QuoteEstado } from "@/lib/enums";
import type { QuoteEstimate } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Button,
  Divider,
  Group,
  NumberInput,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconCheck, IconFileText, IconPlus, IconX } from "@tabler/icons-react";

const ESTADO_COLOR: Record<QuoteEstado, string> = {
  [QuoteEstado.BORRADOR]: "gray",
  [QuoteEstado.ENVIADA]: "blue",
  [QuoteEstado.ACEPTADA]: "green",
  [QuoteEstado.RECHAZADA]: "red",
};

const ESTADO_LABEL: Record<QuoteEstado, string> = {
  [QuoteEstado.BORRADOR]: "Borrador",
  [QuoteEstado.ENVIADA]: "Enviada",
  [QuoteEstado.ACEPTADA]: "Aceptada",
  [QuoteEstado.RECHAZADA]: "Rechazada",
};

function QuoteCard({ quote }: { quote: QuoteEstimate }) {
  const { mutate: update, isPending } = useUpdateQuote();

  function transition(estado: QuoteEstado) {
    update({ id: quote.id, dto: { estado } });
  }

  return (
    <Paper p="sm" radius="md" withBorder>
      <Group justify="space-between" align="flex-start">
        <Stack gap={4}>
          <Group gap="xs">
            <Badge color={ESTADO_COLOR[quote.estado]} variant="light" size="sm">
              {ESTADO_LABEL[quote.estado]}
            </Badge>
            <Text fz={11} c="dimmed">
              {new Date(quote.created_at).toLocaleDateString("es-AR", {
                day: "2-digit",
                month: "short",
              })}
            </Text>
          </Group>
          <Text fw={700} fz={18} c="indigo">
            ${Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(quote.total)}
          </Text>
          {quote.notas && (
            <Text fz={12} c="dimmed">
              {quote.notas}
            </Text>
          )}
        </Stack>

        {quote.estado === QuoteEstado.ENVIADA && (
          <Group gap={4}>
            <ActionIcon
              variant="light"
              color="green"
              size="sm"
              radius="md"
              loading={isPending}
              onClick={() => transition(QuoteEstado.ACEPTADA)}
              aria-label="Marcar cotización como aceptada"
            >
              <IconCheck size={14} />
            </ActionIcon>
            <ActionIcon
              variant="light"
              color="red"
              size="sm"
              radius="md"
              loading={isPending}
              onClick={() => transition(QuoteEstado.RECHAZADA)}
              aria-label="Marcar cotización como rechazada"
            >
              <IconX size={14} />
            </ActionIcon>
          </Group>
        )}

        {quote.estado === QuoteEstado.BORRADOR && (
          <Button
            size="xs"
            variant="light"
            color="blue"
            radius="md"
            loading={isPending}
            onClick={() => transition(QuoteEstado.ENVIADA)}
            aria-label="Marcar cotización como enviada"
          >
            Enviar
          </Button>
        )}
      </Group>
    </Paper>
  );
}

interface CreateQuoteFormProps {
  leadId: string;
  onClose: () => void;
}

function CreateQuoteForm({ leadId, onClose }: CreateQuoteFormProps) {
  const { mutate: create, isPending } = useCreateQuote();
  const form = useForm({
    initialValues: { total: 0, notas: "" },
    validate: {
      total: (v) => (v <= 0 ? "El total debe ser mayor a 0" : null),
    },
  });

  function handleSubmit(values: { total: number; notas: string }) {
    create(
      { lead_id: leadId, total: values.total, ...(values.notas ? { notas: values.notas } : {}) },
      { onSuccess: onClose },
    );
  }

  return (
    <Paper p="sm" radius="md" withBorder style={{ borderStyle: "dashed" }}>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <NumberInput
            label="Total de la cotización ($)"
            placeholder="15000"
            radius="md"
            size="sm"
            min={0}
            hideControls
            aria-label="Total de la cotización"
            {...form.getInputProps("total")}
          />
          <Textarea
            label="Notas (opcional)"
            placeholder="Incluye instalación y garantía 12 meses…"
            radius="md"
            size="sm"
            minRows={2}
            aria-label="Notas de la cotización"
            {...form.getInputProps("notas")}
          />
          <Group gap="sm" justify="flex-end">
            <Button size="xs" variant="subtle" color="gray" radius="md" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              type="submit"
              size="xs"
              color="indigo"
              radius="md"
              loading={isPending}
              aria-label="Guardar cotización"
            >
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Paper>
  );
}

interface QuotePanelProps {
  leadId: string;
}

export function QuotePanel({ leadId }: QuotePanelProps) {
  const { data, isLoading } = useQuotes(leadId);
  const [showForm, { open: openForm, close: closeForm }] = useDisclosure(false);

  if (isLoading) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} height={72} radius="md" />
        ))}
      </Stack>
    );
  }

  const quotes = data?.data ?? [];

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <Text fz={12} fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: "0.04em" }}>
          Cotizaciones
        </Text>
        {!showForm && (
          <Button
            size="xs"
            variant="light"
            color="indigo"
            radius="md"
            leftSection={<IconPlus size={14} />}
            onClick={openForm}
            aria-label="Nueva cotización"
          >
            Nueva
          </Button>
        )}
      </Group>

      {showForm && <CreateQuoteForm leadId={leadId} onClose={closeForm} />}

      {quotes.length > 0 ? (
        <>
          {showForm && <Divider />}
          {quotes.map((q) => (
            <QuoteCard key={q.id} quote={q} />
          ))}
        </>
      ) : (
        !showForm && (
          <Stack align="center" gap="xs" py="md">
            <ThemeIcon size={40} radius="xl" color="gray" variant="light" aria-hidden="true">
              <IconFileText size={20} />
            </ThemeIcon>
            <Text size="sm" c="dimmed" ta="center">
              Sin cotizaciones para este lead.
            </Text>
          </Stack>
        )
      )}
    </Stack>
  );
}
