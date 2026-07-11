"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import type { VentasFilters } from "@/hooks/useVentas";
import { useDeleteVenta, useVentas } from "@/hooks/useVentas";
import { SEMANTIC } from "@/lib/theme-tokens";
import type { Venta } from "@/lib/types";
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
import { IconDotsVertical, IconTrash } from "@tabler/icons-react";

interface VentasTableProps {
  filters?: VentasFilters;
  onPageChange?: (page: number) => void;
}

export function VentasTable({ filters, onPageChange }: VentasTableProps) {
  const { data, isLoading } = useVentas({ page_size: 20, ...filters });
  const { mutate: deleteVenta } = useDeleteVenta();

  const ventas = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;
  const currentPage = filters?.page ?? 1;

  function confirmAnular(v: Venta) {
    modals.openConfirmModal({
      title: "Anular venta",
      children: (
        <Text size="sm">
          ¿Anular la venta del <strong>{new Date(v.created_at).toLocaleDateString("es-AR")}</strong>
          ?
        </Text>
      ),
      labels: { confirm: "Anular", cancel: "Cancelar" },
      confirmProps: { color: "red" },
      onConfirm: () => deleteVenta(v.id),
    });
  }

  return (
    <Stack gap="md">
      <Table.ScrollContainer minWidth={700}>
        <Table striped highlightOnHover verticalSpacing="sm" aria-label="Tabla de ventas">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Fecha</Table.Th>
              <Table.Th>Lead ID</Table.Th>
              <Table.Th>Producto ID</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Total</Table.Th>
              <Table.Th>IA</Table.Th>
              <Table.Th aria-label="Acciones" />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Table.Tr key={i}>
                  {Array.from({ length: 6 }).map((__, j) => (
                    <Table.Td key={j}>
                      <Skeleton height={16} radius="sm" />
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))
            ) : ventas.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <EmptyState
                    icon="💰"
                    title="Sin ventas"
                    description="Registra tu primera venta."
                  />
                </Table.Td>
              </Table.Tr>
            ) : (
              ventas.map((v) => (
                <Table.Tr key={v.id}>
                  <Table.Td>
                    <Text size="sm">
                      {new Date(v.created_at).toLocaleDateString("es-AR", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed" style={{ fontFamily: "monospace" }}>
                      {v.lead_id.slice(0, 8)}…
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed" style={{ fontFamily: "monospace" }}>
                      {v.producto_id.slice(0, 8)}…
                    </Text>
                  </Table.Td>
                  <Table.Td className="num-tabular">
                    <Text size="sm" fw={700} c={SEMANTIC.successText}>
                      ${Intl.NumberFormat("es", { minimumFractionDigits: 2 }).format(v.total)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={v.ai_assisted ? "violet" : "gray"}
                      variant="light"
                      size="xs"
                      radius="sm"
                    >
                      {v.ai_assisted ? "IA" : "Manual"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Menu width={140} shadow="sm" position="bottom-end">
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="sm"
                          aria-label="Acciones para venta"
                        >
                          <IconDotsVertical size={14} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        <Menu.Item
                          leftSection={<IconTrash size={14} />}
                          color="red"
                          onClick={() => confirmAnular(v)}
                          aria-label="Anular venta"
                        >
                          Anular
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
        <Group justify="flex-end">
          <Pagination
            value={currentPage}
            total={totalPages}
            onChange={(p) => onPageChange?.(p)}
            size="sm"
            radius="md"
            aria-label="Paginación de ventas"
          />
        </Group>
      )}
    </Stack>
  );
}
