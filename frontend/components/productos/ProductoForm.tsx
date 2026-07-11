"use client";

import { useCategorias } from "@/hooks/useCategorias";
import type { CreateProductoDto, UpdateProductoDto } from "@/hooks/useProductos";
import type { Producto } from "@/lib/types";
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect } from "react";

interface ProductoFormValues {
  nombre: string;
  descripcion: string;
  precio: number | string;
  categoria_id: string;
}

interface ProductoFormProps {
  opened: boolean;
  onClose: () => void;
  onSubmit: (dto: CreateProductoDto | UpdateProductoDto) => void;
  isLoading?: boolean;
  producto?: Producto | null;
}

export function ProductoForm({
  opened,
  onClose,
  onSubmit,
  isLoading,
  producto,
}: ProductoFormProps) {
  const { data: categorias } = useCategorias();
  const isEdit = !!producto;

  const form = useForm<ProductoFormValues>({
    initialValues: {
      nombre: "",
      descripcion: "",
      precio: "",
      categoria_id: "",
    },
    validate: {
      nombre: (v) => (v.trim().length < 2 ? "Mínimo 2 caracteres" : null),
      precio: (v) => (Number(v) <= 0 ? "El precio debe ser mayor a 0" : null),
    },
  });

  useEffect(() => {
    if (producto) {
      form.setValues({
        nombre: producto.nombre,
        descripcion: producto.descripcion ?? "",
        precio: producto.precio,
        categoria_id: producto.categoria_id ?? "",
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [producto, opened]);

  function handleSubmit(values: ProductoFormValues) {
    const dto: CreateProductoDto = {
      nombre: values.nombre.trim(),
      precio: Number(values.precio),
      ...(values.descripcion ? { descripcion: values.descripcion.trim() } : {}),
      ...(values.categoria_id ? { categoria_id: values.categoria_id } : {}),
    };
    onSubmit(dto);
  }

  const categoriaOptions = categorias?.map((c) => ({ value: c.id, label: c.nombre })) ?? [];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? "Editar Producto" : "Nuevo Producto"}
      size="md"
      radius="md"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Nombre"
            placeholder="Nombre del producto o servicio"
            required
            aria-label="Nombre del producto"
            radius="md"
            {...form.getInputProps("nombre")}
          />

          <Textarea
            label="Descripción"
            placeholder="Descripción opcional"
            aria-label="Descripción del producto"
            rows={3}
            radius="md"
            {...form.getInputProps("descripcion")}
          />

          <Group grow gap="sm">
            <NumberInput
              label="Precio (USD)"
              placeholder="0.00"
              min={0}
              decimalScale={2}
              prefix="$"
              required
              aria-label="Precio del producto"
              radius="md"
              {...form.getInputProps("precio")}
            />
            <Select
              label="Categoría"
              placeholder="Sin categoría"
              data={categoriaOptions}
              clearable
              aria-label="Categoría del producto"
              radius="md"
              {...form.getInputProps("categoria_id")}
            />
          </Group>

          <Group justify="flex-end" gap="sm" mt="xs">
            <Button variant="subtle" color="gray" onClick={onClose} aria-label="Cancelar">
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={isLoading ?? false}
              color="indigo"
              aria-label={isEdit ? "Guardar cambios" : "Crear producto"}
              radius="md"
            >
              {isEdit ? "Guardar cambios" : "Crear Producto"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
