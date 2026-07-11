"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import type { UpdateProductoDto } from "@/hooks/useProductos";
import { useProductos, useUpdateProducto } from "@/hooks/useProductos";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { ESTADO_STOCK_UI, estadoStock } from "@/lib/inventario";
import { plural, tieneCapacidad } from "@/lib/rubros";
import type { Producto } from "@/lib/types";
import {
  Alert,
  Badge,
  Group,
  NumberInput,
  Pagination,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconPackage, IconSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";

const PAGE_SIZE = 50;
const SKELETON_IDS = ["sk-1", "sk-2", "sk-3", "sk-4", "sk-5"];

function FilaInventario({ producto }: { producto: Producto }) {
  const { mutate: update, isPending } = useUpdateProducto();
  const [stock, setStock] = useState<number>(producto.stock);
  const [minimo, setMinimo] = useState<number>(producto.stock_minimo ?? 0);

  const ui = ESTADO_STOCK_UI[estadoStock(stock, minimo)];

  const guardar = () => {
    const stockCambio = stock !== producto.stock;
    const minimoCambio = minimo !== (producto.stock_minimo ?? 0);
    if (!stockCambio && !minimoCambio) return;
    const dto: UpdateProductoDto = {
      ...(stockCambio ? { stock } : {}),
      ...(minimoCambio ? { stock_minimo: minimo } : {}),
      // Regla espejo del backend: agotar deshabilita el artículo; reponer lo rehabilita.
      ...(stockCambio ? { disponible: stock > 0 } : {}),
    };
    update({ id: producto.id, dto });
  };

  return (
    <Table.Tr>
      <Table.Td>
        <Text size="sm" fw={500}>
          {producto.nombre}
        </Text>
      </Table.Td>
      <Table.Td className="num-tabular">
        <NumberInput
          value={stock}
          onChange={(v) => setStock(typeof v === "number" ? v : 0)}
          onBlur={guardar}
          min={0}
          w={110}
          size="xs"
          disabled={isPending}
          aria-label={`Stock de ${producto.nombre}`}
        />
      </Table.Td>
      <Table.Td className="num-tabular">
        <NumberInput
          value={minimo}
          onChange={(v) => setMinimo(typeof v === "number" ? v : 0)}
          onBlur={guardar}
          min={0}
          w={110}
          size="xs"
          disabled={isPending}
          aria-label={`Stock mínimo de ${producto.nombre}`}
        />
      </Table.Td>
      <Table.Td>
        <Badge color={ui.color} variant="light">
          {ui.label}
        </Badge>
      </Table.Td>
    </Table.Tr>
  );
}

export default function InventarioPage() {
  const rubro = useRubroLabels();
  const [page, setPage] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const { data, isLoading } = useProductos({ page, page_size: PAGE_SIZE });

  const itemLabel = rubro.labels.item;
  const productos = useMemo(() => {
    const rows = data?.data ?? [];
    const q = busqueda.trim().toLowerCase();
    return q ? rows.filter((p) => p.nombre.toLowerCase().includes(q)) : rows;
  }, [data, busqueda]);

  if (!tieneCapacidad(rubro.key, "inventario")) {
    return (
      <Alert color="yellow" title="Módulo no habilitado" icon={<IconPackage size={18} />}>
        El módulo de inventario no está habilitado para este negocio.
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="Inventario"
        subtitle={`Stock de ${plural(itemLabel).toLowerCase()}: ajusta cantidades y el umbral de alerta de stock bajo.`}
      />
      <TextInput
        placeholder={`Buscar ${itemLabel.toLowerCase()}...`}
        leftSection={<IconSearch size={16} />}
        value={busqueda}
        onChange={(e) => setBusqueda(e.currentTarget.value)}
        maw={320}
        aria-label={`Buscar ${itemLabel.toLowerCase()}`}
      />
      {isLoading ? (
        <Stack gap="xs">
          {SKELETON_IDS.map((id) => (
            <Skeleton key={id} height={40} radius="sm" />
          ))}
        </Stack>
      ) : (
        <>
          <Table.ScrollContainer minWidth={600}>
            <Table striped highlightOnHover verticalSpacing="sm" aria-label="Tabla de inventario">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{itemLabel}</Table.Th>
                  <Table.Th style={{ textAlign: "right" }}>Stock</Table.Th>
                  <Table.Th style={{ textAlign: "right" }}>Stock mínimo</Table.Th>
                  <Table.Th>Estado</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {productos.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={4}>
                      <EmptyState
                        title={`No hay ${plural(itemLabel).toLowerCase()} para mostrar.`}
                      />
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  productos.map((p) => <FilaInventario key={p.id} producto={p} />)
                )}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {data && data.meta.total_pages > 1 && (
            <Group justify="flex-end">
              <Pagination
                total={data.meta.total_pages}
                value={page}
                onChange={setPage}
                size="sm"
                radius="md"
                aria-label="Paginación de inventario"
              />
            </Group>
          )}
        </>
      )}
    </Stack>
  );
}
