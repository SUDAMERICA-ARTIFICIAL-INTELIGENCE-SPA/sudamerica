"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import type { ProductosFilters } from "@/hooks/useProductos";
import { useDeleteProducto, useProductos } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
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
  TextInput,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { IconDotsVertical, IconEdit, IconSearch, IconTrash } from "@tabler/icons-react";
import { useState } from "react";

interface ProductosTableProps {
  onEditProducto: (producto: Producto) => void;
}

export function ProductosTable({ onEditProducto }: ProductosTableProps) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { mutate: deleteProducto } = useDeleteProducto();

  const filters: ProductosFilters = {
    page,
    page_size: 20,
    ...(search ? { search } : {}),
  };
  const { data, isLoading } = useProductos(filters);

  const productos = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

  function confirmDelete(p: Producto) {
    modals.openConfirmModal({
      title: "Desactivar producto",
      children: (
        <Text size="sm">
          ¿Desactivar <strong>{p.nombre}</strong>?
        </Text>
      ),
      labels: { confirm: "Desactivar", cancel: "Cancelar" },
      confirmProps: { color: "red" },
      onConfirm: () => deleteProducto(p.id),
    });
  }

  return (
    <Stack gap="md">
      <TextInput
        placeholder="Buscar productos..."
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        aria-label="Buscar productos"
        maw={300}
        radius="md"
      />

      <Table.ScrollContainer minWidth={600}>
        <Table striped highlightOnHover verticalSpacing="sm" aria-label="Tabla de productos">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nombre</Table.Th>
              <Table.Th>Categoría</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Precio</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th aria-label="Acciones" />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Table.Tr key={i}>
                  {Array.from({ length: 5 }).map((__, j) => (
                    <Table.Td key={j}>
                      <Skeleton height={16} radius="sm" />
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))
            ) : productos.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <EmptyState
                    icon="📦"
                    title="Sin productos"
                    description="Agrega tu primer producto."
                  />
                </Table.Td>
              </Table.Tr>
            ) : (
              productos.map((p) => (
                <Table.Tr key={p.id}>
                  <Table.Td>
                    <Text fw={500} size="sm">
                      {p.nombre}
                    </Text>
                    {p.descripcion && (
                      <Text size="xs" c="dimmed" lineClamp={1}>
                        {p.descripcion}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{p.categoria_id ?? "—"}</Text>
                  </Table.Td>
                  <Table.Td className="num-tabular">
                    <Text size="sm" fw={600}>
                      $
                      {Intl.NumberFormat("es", {
                        minimumFractionDigits: 2,
                      }).format(p.precio)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={p.activo ? "green" : "gray"}
                      variant="light"
                      size="sm"
                      radius="sm"
                    >
                      {p.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Menu width={160} shadow="sm" position="bottom-end">
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="sm"
                          aria-label={`Acciones para ${p.nombre}`}
                        >
                          <IconDotsVertical size={14} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        <Menu.Item
                          leftSection={<IconEdit size={14} />}
                          onClick={() => onEditProducto(p)}
                          aria-label={`Editar ${p.nombre}`}
                        >
                          Editar
                        </Menu.Item>
                        <Menu.Divider />
                        <Menu.Item
                          leftSection={<IconTrash size={14} />}
                          color="red"
                          onClick={() => confirmDelete(p)}
                          aria-label={`Desactivar ${p.nombre}`}
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
        <Group justify="flex-end">
          <Pagination
            value={page}
            total={totalPages}
            onChange={setPage}
            size="sm"
            radius="md"
            aria-label="Paginación de productos"
          />
        </Group>
      )}
    </Stack>
  );
}
