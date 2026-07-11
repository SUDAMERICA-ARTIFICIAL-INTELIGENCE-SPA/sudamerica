"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { ScoreThermometer } from "@/components/ui/ScoreThermometer";
import type { LeadsFilters } from "@/hooks/useLeads";
import { useDeleteLead, useLeads } from "@/hooks/useLeads";
import { LeadEstado } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import {
  ActionIcon,
  Badge,
  Group,
  Menu,
  Pagination,
  Skeleton,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { IconDotsVertical, IconEdit, IconEye, IconTrash } from "@tabler/icons-react";

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

interface LeadsTableProps {
  filters: LeadsFilters;
  onPageChange: (page: number) => void;
  onViewLead: (lead: Lead) => void;
  onEditLead: (lead: Lead) => void;
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <Table.Tr key={i}>
          {Array.from({ length: 7 }).map((__, j) => (
            <Table.Td key={j}>
              <Skeleton height={16} radius="sm" />
            </Table.Td>
          ))}
        </Table.Tr>
      ))}
    </>
  );
}

export function LeadsTable({ filters, onPageChange, onViewLead, onEditLead }: LeadsTableProps) {
  const { data, isLoading } = useLeads({ ...filters, page_size: 20 });
  const { mutate: deleteLead } = useDeleteLead();

  function confirmDelete(lead: Lead) {
    modals.openConfirmModal({
      title: "Desactivar cliente",
      children: (
        <Text size="sm">
          ¿Estás seguro de que quieres desactivar a <strong>{lead.nombre}</strong>?
        </Text>
      ),
      labels: { confirm: "Desactivar", cancel: "Cancelar" },
      confirmProps: { color: "red" },
      onConfirm: () => deleteLead(lead.id),
    });
  }

  const leads = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;
  const currentPage = filters.page ?? 1;

  return (
    <Stack gap="md">
      <Table.ScrollContainer minWidth={600}>
        <Table
          striped
          highlightOnHover
          withColumnBorders={false}
          verticalSpacing="sm"
          aria-label="Tabla de clientes"
        >
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nombre</Table.Th>
              <Table.Th>Canal</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Valor Est.</Table.Th>
              <Table.Th>Score IA</Table.Th>
              <Table.Th>Creado</Table.Th>
              <Table.Th aria-label="Acciones" />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <SkeletonRows />
            ) : leads.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <EmptyState
                    icon="👤"
                    title="Sin clientes"
                    description="Registra tu primer cliente con el botón '+'"
                  />
                </Table.Td>
              </Table.Tr>
            ) : (
              leads.map((lead) => (
                <Table.Tr
                  key={lead.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => onViewLead(lead)}
                >
                  <Table.Td>
                    <Text fw={500} size="sm">
                      {lead.nombre}
                    </Text>
                    {lead.email && (
                      <Text size="xs" c="dimmed">
                        {lead.email}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{lead.canal}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={ESTADO_COLOR[lead.estado]} variant="light" size="sm" radius="sm">
                      {ESTADO_LABEL[lead.estado]}
                    </Badge>
                  </Table.Td>
                  <Table.Td className="num-tabular">
                    <Text size="sm">
                      {lead.valor_estimado !== null
                        ? `$${Intl.NumberFormat("es").format(lead.valor_estimado)}`
                        : "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td onClick={(e) => e.stopPropagation()}>
                    <ScoreThermometer score={lead.ai_score} />
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {new Date(lead.created_at).toLocaleDateString("es-AR", {
                        day: "2-digit",
                        month: "short",
                      })}
                    </Text>
                  </Table.Td>
                  <Table.Td onClick={(e) => e.stopPropagation()}>
                    <Menu width={160} shadow="sm" position="bottom-end">
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="sm"
                          aria-label={`Acciones para ${lead.nombre}`}
                        >
                          <IconDotsVertical size={14} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        <Menu.Item
                          leftSection={<IconEye size={14} />}
                          onClick={() => onViewLead(lead)}
                          aria-label={`Ver detalle de ${lead.nombre}`}
                        >
                          Ver detalle
                        </Menu.Item>
                        <Menu.Item
                          leftSection={<IconEdit size={14} />}
                          onClick={() => onEditLead(lead)}
                          aria-label={`Editar ${lead.nombre}`}
                        >
                          Editar
                        </Menu.Item>
                        <Menu.Divider />
                        <Menu.Item
                          leftSection={<IconTrash size={14} />}
                          color="red"
                          onClick={() => confirmDelete(lead)}
                          aria-label={`Desactivar ${lead.nombre}`}
                        >
                          Desactivar
                        </Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      {totalPages > 1 && (
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {data?.meta.total ?? 0} clientes totales
          </Text>
          <Pagination
            value={currentPage}
            total={totalPages}
            onChange={onPageChange}
            size="sm"
            radius="md"
            aria-label="Paginación de clientes"
          />
        </Group>
      )}
    </Stack>
  );
}
