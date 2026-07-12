"use client";

import { AIAgentSettings } from "@/components/configuracion/AIAgentSettings";
import { AvailabilityInstructions } from "@/components/configuracion/AvailabilityInstructions";
import { TrainingChat } from "@/components/training/TrainingChat";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useAgenteConfigRaw, useUpdateAgentProfile } from "@/hooks/useAgenteConfig";
import { useDeleteKnowledge, useKnowledge, useTeach } from "@/hooks/useTraining";
import type { KnowledgeEntry } from "@/hooks/useTraining";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import {
  IconBook2,
  IconBrain,
  IconMessageChatbot,
  IconRobot,
  IconSettings,
  IconTrash,
} from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";

// ── Knowledge Card ──────────────────────────────────────────────────────────

function KnowledgeCard({
  entry,
  onDelete,
  isDeleting,
}: {
  entry: KnowledgeEntry;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}) {
  return (
    <Card withBorder radius="md" padding="sm">
      <Group justify="space-between" wrap="nowrap" mb={4}>
        <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
          <IconBook2 size={16} style={{ flexShrink: 0, color: "var(--mantine-color-indigo-5)" }} />
          <Text fw={600} fz="sm" truncate="end">
            {entry.title}
          </Text>
        </Group>
        <Group gap={4} wrap="nowrap" style={{ flexShrink: 0 }}>
          <Badge size="xs" variant="light" color="indigo">
            {entry.type}
          </Badge>
          <Tooltip label="Eliminar" position="left">
            <ActionIcon
              variant="subtle"
              color="red"
              size="sm"
              onClick={() => onDelete(entry.id)}
              loading={isDeleting}
              aria-label={`Eliminar ${entry.title}`}
            >
              <IconTrash size={14} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
      <Text fz="xs" c="dimmed" lineClamp={3}>
        {entry.content}
      </Text>
    </Card>
  );
}

// ── Tab: Personalidad ───────────────────────────────────────────────────────

function PersonalidadTab() {
  const { data: config, isLoading } = useAgenteConfigRaw();
  const { mutate: saveProfile, isPending } = useUpdateAgentProfile();
  const [nombreAgente, setNombreAgente] = useState("");
  const [personalidad, setPersonalidad] = useState("");

  useEffect(() => {
    if (config) {
      setNombreAgente((config.nombre_agente as string) ?? "");
      setPersonalidad((config.personalidad as string) ?? "");
    }
  }, [config]);

  if (isLoading) return <Skeleton height={200} radius="md" />;

  return (
    <Stack gap="md">
      <SectionCard
        title="Identidad del Agente"
        subtitle="Define como se presenta tu IA ante los clientes. El nombre aparece en las conversaciones y la personalidad guia el tono de todas las respuestas."
      >
        <Stack gap="md">
          <TextInput
            label="Nombre del agente"
            placeholder="Ej: Sofia, SudaméricaBot, ChefIA..."
            description="Asi se presentara ante tus clientes por WhatsApp"
            value={nombreAgente}
            onChange={(e) => setNombreAgente(e.currentTarget.value)}
            radius="md"
          />
          <Textarea
            label="Personalidad e instrucciones generales"
            placeholder={
              "Ej: Soy la asistente virtual del restaurant. Soy amable, uso emojis con moderacion, tuteo al cliente.\nSiempre ofrezco los combos del dia. Si el cliente pregunta por delivery, pregunto direccion y comuna."
            }
            value={personalidad}
            onChange={(e) => setPersonalidad(e.currentTarget.value)}
            minRows={5}
            maxRows={10}
            autosize
            radius="md"
          />
          <Group justify="flex-end">
            <Button
              onClick={() => saveProfile({ nombre_agente: nombreAgente, personalidad })}
              loading={isPending}
              color="indigo"
              radius="md"
            >
              Guardar identidad
            </Button>
          </Group>
        </Stack>
      </SectionCard>

      <SectionCard
        title="Disponibilidad y Sustituciones"
        subtitle="Cuando un plato no esta disponible, la IA sigue estas reglas para ofrecer alternativas."
      >
        <AvailabilityInstructions />
      </SectionCard>
    </Stack>
  );
}

// ── Tab: Conocimiento ───────────────────────────────────────────────────────

const KNOWLEDGE_PROMPTS = [
  {
    label: "Horarios y ubicacion",
    placeholder:
      "Lunes a sabado 12:00 a 23:00, domingos 12:00 a 17:00. Estamos en Av. Providencia 1234. Estacionamiento gratuito para clientes.",
  },
  {
    label: "Politicas de delivery",
    placeholder:
      "Delivery gratis sobre $15.000. Zona de cobertura: Providencia, Las Condes, Nunoa. Tiempo estimado 30-45 min.",
  },
  {
    label: "Metodos de pago",
    placeholder:
      "Aceptamos efectivo, tarjeta (debito/credito), transferencia bancaria. Propina incluida en pedidos delivery.",
  },
  {
    label: "Reservas y eventos",
    placeholder:
      "Aceptamos reservas para grupos de hasta 20 personas. Para eventos privados, pedir cotizacion.",
  },
  {
    label: "Alergenos e informacion nutricional",
    placeholder:
      "Todos nuestros platos pueden contener trazas de frutos secos. Opciones sin gluten disponibles bajo pedido.",
  },
  {
    label: "Promociones activas",
    placeholder:
      "2x1 en pizzas los martes. Happy hour de 18:00 a 20:00 (cerveza + papas $5.990). Combo almuerzo $7.990.",
  },
];

function ConocimientoTab() {
  const [content, setContent] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const knowledge = useKnowledge();
  const teach = useTeach();
  const deleteKnowledge = useDeleteKnowledge();

  const entries: KnowledgeEntry[] = knowledge.data?.data ?? [];

  const handleTeach = useCallback(() => {
    if (content.trim().length < 10) return;
    teach.mutate(content, { onSuccess: () => setContent("") });
  }, [content, teach]);

  const handleDelete = useCallback(
    (id: string) => {
      setDeletingId(id);
      deleteKnowledge.mutate(id, { onSettled: () => setDeletingId(null) });
    },
    [deleteKnowledge],
  );

  const handlePromptClick = (placeholder: string) => {
    if (!content) setContent(placeholder);
  };

  return (
    <Stack gap="md">
      {/* Quick-teach prompts */}
      <SectionCard
        title="Ensenale a tu IA"
        subtitle="Agrega informacion que la IA debe saber sobre tu restaurant. Mientras mas contexto le des, mejor atendera a tus clientes."
      >
        <Stack gap="md">
          <Text fz="xs" fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: "0.04em" }}>
            Temas sugeridos (haz clic para usar como plantilla)
          </Text>
          <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="xs">
            {KNOWLEDGE_PROMPTS.map((p) => (
              <Button
                key={p.label}
                variant="light"
                color="gray"
                size="xs"
                radius="md"
                onClick={() => handlePromptClick(p.placeholder)}
                style={{
                  height: "auto",
                  padding: "8px 12px",
                  whiteSpace: "normal",
                  textAlign: "left",
                }}
              >
                {p.label}
              </Button>
            ))}
          </SimpleGrid>

          <Textarea
            placeholder="Escribe informacion que la IA debe saber..."
            minRows={5}
            maxRows={12}
            autosize
            value={content}
            onChange={(e) => setContent(e.currentTarget.value)}
            radius="md"
          />
          <Group justify="flex-end">
            <Button
              onClick={handleTeach}
              loading={teach.isPending}
              disabled={content.trim().length < 10}
              color="indigo"
              radius="md"
            >
              Guardar conocimiento
            </Button>
          </Group>
        </Stack>
      </SectionCard>

      {/* Knowledge list */}
      <SectionCard
        title="Conocimiento guardado"
        action={
          <Badge variant="light" color="indigo" size="sm">
            {entries.length} {entries.length === 1 ? "entrada" : "entradas"}
          </Badge>
        }
      >
        {knowledge.isLoading && (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={`skel-${i}`} height={100} radius="md" />
            ))}
          </SimpleGrid>
        )}

        {!knowledge.isLoading && entries.length === 0 && (
          <EmptyState title="Aun no has ensenado nada a la IA. Usa los temas sugeridos arriba para empezar." />
        )}

        {entries.length > 0 && (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm">
            {entries.map((entry) => (
              <KnowledgeCard
                key={entry.id}
                entry={entry}
                onDelete={handleDelete}
                isDeleting={deletingId === entry.id}
              />
            ))}
          </SimpleGrid>
        )}
      </SectionCard>
    </Stack>
  );
}

// ── Tab: Comportamiento ─────────────────────────────────────────────────────

function ComportamientoTab() {
  return (
    <Stack gap="md">
      <SectionCard
        title="Sub-agentes de IA"
        subtitle="Activa o desactiva los modulos especializados de tu agente. Cada uno maneja un tipo de interaccion diferente."
      >
        <AIAgentSettings />
      </SectionCard>
    </Stack>
  );
}

// ── Tab: Probar ─────────────────────────────────────────────────────────────

function ProbarTab() {
  return (
    <Stack gap="md">
      <SectionCard
        title="Probar tu agente"
        subtitle="Conversa con tu IA para verificar que responde correctamente usando el conocimiento y la personalidad que configuraste."
      >
        <TrainingChat />
      </SectionCard>
    </Stack>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function ConfiguracionIAPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Configuracion IA"
        subtitle="Personaliza como tu agente de IA interactua con los clientes de tu restaurant."
      />

      <Tabs defaultValue="personalidad" keepMounted={false}>
        <Tabs.List mb="lg">
          <Tabs.Tab value="personalidad" leftSection={<IconRobot size={16} />}>
            Personalidad
          </Tabs.Tab>
          <Tabs.Tab value="conocimiento" leftSection={<IconBrain size={16} />}>
            Conocimiento
          </Tabs.Tab>
          <Tabs.Tab value="comportamiento" leftSection={<IconSettings size={16} />}>
            Comportamiento
          </Tabs.Tab>
          <Tabs.Tab value="probar" leftSection={<IconMessageChatbot size={16} />}>
            Probar IA
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="personalidad">
          <PersonalidadTab />
        </Tabs.Panel>

        <Tabs.Panel value="conocimiento">
          <ConocimientoTab />
        </Tabs.Panel>

        <Tabs.Panel value="comportamiento">
          <ComportamientoTab />
        </Tabs.Panel>

        <Tabs.Panel value="probar">
          <ProbarTab />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
