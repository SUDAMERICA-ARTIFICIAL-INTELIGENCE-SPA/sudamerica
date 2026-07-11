"use client";

import { useLeads } from "@/hooks/useLeads";
import { useProductos } from "@/hooks/useProductos";
import type { CreateVentaDto } from "@/hooks/useVentas";
import { Button, Checkbox, Group, Modal, Select, Stack, Text } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconRobot } from "@tabler/icons-react";

interface VentaFormValues {
  lead_id: string;
  producto_id: string;
  ai_assisted: boolean;
}

interface VentaFormProps {
  opened: boolean;
  onClose: () => void;
  onSubmit: (dto: CreateVentaDto) => void;
  isLoading?: boolean;
}

export function VentaForm({ opened, onClose, onSubmit, isLoading }: VentaFormProps) {
  const { data: leadsData } = useLeads({ page_size: 100 });
  const { data: productosData } = useProductos({
    page_size: 100,
    activo: true,
  });

  const form = useForm<VentaFormValues>({
    initialValues: { lead_id: "", producto_id: "", ai_assisted: false },
    validate: {
      lead_id: (v) => (v ? null : "Selecciona un lead"),
      producto_id: (v) => (v ? null : "Selecciona un producto"),
    },
  });

  function handleSubmit(values: VentaFormValues) {
    onSubmit(values);
  }

  const leadOptions =
    leadsData?.data.map((l) => ({
      value: l.id,
      label: `${l.nombre}${l.valor_estimado !== null ? ` — $${l.valor_estimado}` : ""}`,
    })) ?? [];

  const productoOptions =
    productosData?.data.map((p) => ({
      value: p.id,
      label: `${p.nombre} — $${p.precio}`,
    })) ?? [];

  return (
    <Modal
      opened={opened}
      onClose={() => {
        form.reset();
        onClose();
      }}
      title="Registrar Venta"
      size="md"
      radius="md"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <Text size="xs" c="dimmed">
            El total será calculado automáticamente por el servidor.
          </Text>

          <Select
            label="Lead"
            placeholder="Selecciona el lead"
            data={leadOptions}
            searchable
            required
            aria-label="Lead de la venta"
            radius="md"
            {...form.getInputProps("lead_id")}
          />

          <Select
            label="Producto"
            placeholder="Selecciona el producto"
            data={productoOptions}
            searchable
            required
            aria-label="Producto de la venta"
            radius="md"
            {...form.getInputProps("producto_id")}
          />

          <Checkbox
            label={
              <Group gap={6}>
                <IconRobot size={14} />
                <span>Asistida por IA</span>
              </Group>
            }
            aria-label="Venta asistida por IA"
            {...form.getInputProps("ai_assisted", { type: "checkbox" })}
          />

          <Group justify="flex-end" gap="sm" mt="xs">
            <Button
              variant="subtle"
              color="gray"
              onClick={() => {
                form.reset();
                onClose();
              }}
              aria-label="Cancelar"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={isLoading ?? false}
              color="indigo"
              aria-label="Registrar venta"
              radius="md"
            >
              Registrar Venta
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
