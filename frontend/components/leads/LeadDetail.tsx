"use client";

import { InteractionForm } from "@/components/leads/InteractionForm";
import { LeadTimeline } from "@/components/leads/LeadTimeline";
import { QuotePanel } from "@/components/leads/QuotePanel";
import { SubentidadesPanel } from "@/components/leads/SubentidadesPanel";
import { ScoreThermometer } from "@/components/ui/ScoreThermometer";
import { useUpdateLead } from "@/hooks/useLeads";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { LEAD_TRANSITIONS, LeadCanal, LeadEstado, canTransition } from "@/lib/enums";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import type { Lead } from "@/lib/types";
import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import {
  IconBrandFacebook,
  IconBrandInstagram,
  IconBrandWhatsapp,
  IconEdit,
  IconFileText,
  IconHeart,
  IconHistory,
  IconInfoCircle,
  IconListDetails,
  IconMail,
  IconPhone,
  IconWorld,
} from "@tabler/icons-react";
import type { ReactNode } from "react";

const CANAL_ICON: Record<LeadCanal, ReactNode> = {
  [LeadCanal.WHATSAPP]: <IconBrandWhatsapp size={14} />,
  [LeadCanal.INSTAGRAM]: <IconBrandInstagram size={14} />,
  [LeadCanal.FACEBOOK]: <IconBrandFacebook size={14} />,
  [LeadCanal.WEB]: <IconWorld size={14} />,
  [LeadCanal.TELEFONO]: <IconPhone size={14} />,
  [LeadCanal.EMAIL]: <IconMail size={14} />,
  [LeadCanal.REFERIDO]: <IconMail size={14} />,
};

const ESTADO_COLOR: Record<LeadEstado, string> = {
  [LeadEstado.NUEVO]: "blue",
  [LeadEstado.CONTACTADO]: "cyan",
  [LeadEstado.EN_PROCESO]: "yellow",
  [LeadEstado.CONVERTIDO]: "green",
  [LeadEstado.DESCARTADO]: "gray",
};

const ESTADO_LABEL: Record<LeadEstado, string> = {
  [LeadEstado.NUEVO]: "Nuevo",
  [LeadEstado.CONTACTADO]: "Contactado",
  [LeadEstado.EN_PROCESO]: "En Proceso",
  [LeadEstado.CONVERTIDO]: "Convertido",
  [LeadEstado.DESCARTADO]: "Descartado",
};

interface DetailFieldProps {
  label: string;
  value: ReactNode;
}

function DetailField({ label, value }: DetailFieldProps) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.04em" }}>
        {label}
      </Text>
      <Text size="sm" fw={500} component="div">
        {value ?? (
          <Text span c="dimmed">
            —
          </Text>
        )}
      </Text>
    </Stack>
  );
}

interface LeadDetailProps {
  lead: Lead | null;
  opened: boolean;
  onClose: () => void;
  onEdit: (lead: Lead) => void;
}

export function LeadDetail({ lead, opened, onClose, onEdit }: LeadDetailProps) {
  const { mutate: updateLead, isPending: isUpdating } = useUpdateLead();
  const rubro = useRubroLabels();
  const platoFavoritoLabel =
    rubro.key === RUBRO_DEFAULT ? "Plato favorito" : `${rubro.labels.item} favorito`;
  // Ficha de sub-entidad (F6): label presente ⟺ ficha activa (invariante del SSOT).
  const subEntidadLabel = rubro.subEntidadLabel;

  function handleTransition(newEstado: LeadEstado) {
    if (!lead) return;
    updateLead({ id: lead.id, dto: { estado: newEstado } });
  }

  const availableTransitions = lead ? LEAD_TRANSITIONS[lead.estado] : [];

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="sm">
          <Title order={4}>{lead?.nombre ?? "Cliente"}</Title>
          {lead && (
            <Badge color={ESTADO_COLOR[lead.estado]} variant="light" size="sm">
              {ESTADO_LABEL[lead.estado]}
            </Badge>
          )}
        </Group>
      }
      position="right"
      size="lg"
      padding="md"
    >
      {lead ? (
        <Tabs defaultValue="datos" keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab
              value="datos"
              leftSection={<IconInfoCircle size={14} />}
              aria-label="Información del cliente"
            >
              Datos
            </Tabs.Tab>
            <Tabs.Tab
              value="timeline"
              leftSection={<IconHistory size={14} />}
              aria-label="Historial de actividad"
            >
              Historial
            </Tabs.Tab>
            <Tabs.Tab
              value="fidelizacion"
              leftSection={<IconHeart size={14} />}
              aria-label="Fidelización del cliente"
            >
              Fidelizacion
            </Tabs.Tab>
            <Tabs.Tab
              value="cotizaciones"
              leftSection={<IconFileText size={14} />}
              aria-label="Cotizaciones del cliente"
            >
              Cotizaciones
            </Tabs.Tab>
            {subEntidadLabel && (
              <Tabs.Tab
                value="subentidades"
                leftSection={<IconListDetails size={14} />}
                aria-label={`${plural(subEntidadLabel)} del cliente`}
              >
                {plural(subEntidadLabel)}
              </Tabs.Tab>
            )}
          </Tabs.List>

          {/* ── Tab 1: Datos ── */}
          <Tabs.Panel value="datos">
            <Stack gap="lg">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailField
                  label="Email"
                  value={
                    lead.email ? (
                      <a href={`mailto:${lead.email}`} style={{ color: "inherit" }}>
                        {lead.email}
                      </a>
                    ) : null
                  }
                />
                <DetailField
                  label="Teléfono"
                  value={
                    lead.telefono ? (
                      <a href={`tel:${lead.telefono}`} style={{ color: "inherit" }}>
                        {lead.telefono}
                      </a>
                    ) : null
                  }
                />
                <DetailField
                  label="Canal"
                  value={
                    <Group gap={4}>
                      {CANAL_ICON[lead.canal]}
                      <span>{lead.canal}</span>
                    </Group>
                  }
                />
                <DetailField
                  label="Valor Estimado"
                  value={
                    lead.valor_estimado !== null
                      ? `$${Intl.NumberFormat("es").format(lead.valor_estimado)}`
                      : null
                  }
                />
              </SimpleGrid>

              <Divider />

              <Stack gap="xs">
                <Text
                  size="xs"
                  c="dimmed"
                  tt="uppercase"
                  fw={600}
                  style={{ letterSpacing: "0.04em" }}
                >
                  Score IA
                </Text>
                <ScoreThermometer score={lead.ai_score} showLabel />
              </Stack>

              <Divider />

              {availableTransitions.length > 0 && (
                <Stack gap="xs">
                  <Text
                    size="xs"
                    c="dimmed"
                    tt="uppercase"
                    fw={600}
                    style={{ letterSpacing: "0.04em" }}
                  >
                    Cambiar estado
                  </Text>
                  <Group gap="xs">
                    {availableTransitions.map((estado) => (
                      <Button
                        key={estado}
                        size="xs"
                        variant="light"
                        color={ESTADO_COLOR[estado]}
                        loading={isUpdating}
                        disabled={!canTransition(lead.estado, estado)}
                        onClick={() => handleTransition(estado)}
                        aria-label={`Mover cliente a ${ESTADO_LABEL[estado]}`}
                        radius="md"
                      >
                        → {ESTADO_LABEL[estado]}
                      </Button>
                    ))}
                  </Group>
                </Stack>
              )}

              <Divider />

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailField
                  label="Creado"
                  value={new Date(lead.created_at).toLocaleDateString("es-AR", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                />
                <DetailField
                  label="Actualizado"
                  value={new Date(lead.updated_at).toLocaleDateString("es-AR", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                />
              </SimpleGrid>

              <Divider />

              <Group gap="sm">
                <Button
                  leftSection={<IconEdit size={16} />}
                  variant="light"
                  color="indigo"
                  onClick={() => onEdit(lead)}
                  aria-label="Editar cliente"
                  radius="md"
                >
                  Editar
                </Button>
              </Group>
            </Stack>
          </Tabs.Panel>

          {/* ── Tab: Fidelización ── */}
          <Tabs.Panel value="fidelizacion">
            <Stack gap="md">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <DetailField
                  label="Tipo de cliente"
                  value={
                    lead.estado_cliente ? (
                      <Badge
                        color={
                          lead.estado_cliente === "VIP"
                            ? "yellow"
                            : lead.estado_cliente === "FRECUENTE"
                              ? "green"
                              : lead.estado_cliente === "INACTIVO"
                                ? "red"
                                : "blue"
                        }
                        variant="light"
                      >
                        {lead.estado_cliente}
                      </Badge>
                    ) : null
                  }
                />
                <DetailField label={platoFavoritoLabel} value={lead.plato_favorito} />
                <DetailField label="Total pedidos" value={lead.total_pedidos ?? 0} />
                <DetailField
                  label="Total gastado"
                  value={
                    lead.total_gastado
                      ? `$${Intl.NumberFormat("es-CL").format(lead.total_gastado)}`
                      : "$0"
                  }
                />
                <DetailField
                  label="Ultima visita"
                  value={
                    lead.ultima_visita
                      ? new Date(lead.ultima_visita).toLocaleDateString("es-AR", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })
                      : null
                  }
                />
                <DetailField label="Frecuencia (dias)" value={lead.frecuencia_dias ?? null} />
              </SimpleGrid>
            </Stack>
          </Tabs.Panel>

          {/* ── Tab 2: Timeline ── */}
          <Tabs.Panel value="timeline">
            <Stack gap="md">
              <InteractionForm leadId={lead.id} />
              <Divider />
              <LeadTimeline leadId={lead.id} />
            </Stack>
          </Tabs.Panel>

          {/* ── Tab 3: Cotizaciones ── */}
          <Tabs.Panel value="cotizaciones">
            <QuotePanel leadId={lead.id} />
          </Tabs.Panel>

          {/* ── Tab: Sub-entidades (solo rubros con módulo sub_entidad) ── */}
          {subEntidadLabel && (
            <Tabs.Panel value="subentidades">
              <SubentidadesPanel leadId={lead.id} label={subEntidadLabel} />
            </Tabs.Panel>
          )}
        </Tabs>
      ) : (
        <Stack gap="md">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={40} radius="sm" />
          ))}
        </Stack>
      )}
    </Drawer>
  );
}
