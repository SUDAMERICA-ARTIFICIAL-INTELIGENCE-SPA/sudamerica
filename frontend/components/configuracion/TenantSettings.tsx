"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { RUBRO_DEFAULT } from "@/lib/rubros";
import {
  Button,
  Group,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useState } from "react";

const TIPO_COCINA_OPTIONS = [
  "Comida Chilena",
  "Comida Peruana",
  "Comida Mexicana",
  "Comida Italiana",
  "Comida Japonesa / Sushi",
  "Comida China",
  "Parrilla / Asados",
  "Mariscos / Pescados",
  "Pizzería",
  "Hamburguesas",
  "Comida Rápida",
  "Cafetería / Bakery",
  "Heladería",
  "Bar / Pub",
  "Food Truck",
  "Vegano / Vegetariano",
  "Fusión",
  "Otro",
].map((v) => ({ value: v, label: v }));

const MODALIDAD_OPTIONS = [
  { value: "mesa", label: "Solo mesa" },
  { value: "delivery", label: "Solo delivery" },
  { value: "takeaway", label: "Solo takeaway" },
  { value: "mesa_delivery", label: "Mesa + Delivery" },
  { value: "mesa_takeaway", label: "Mesa + Takeaway" },
  { value: "todos", label: "Mesa + Delivery + Takeaway" },
];

export function TenantSettings() {
  const { user } = useAuth();
  const rubro = useRubroLabels();
  const isDefault = rubro.key === RUBRO_DEFAULT;
  const isGastro = rubro.sector === "gastronomia";
  const [loading, setLoading] = useState(false);
  const sectionTitle = isDefault ? "Datos del Restaurant" : "Datos del negocio";

  const form = useForm({
    initialValues: {
      nombre: user?.nombre ?? "",
      tipo_cocina: "",
      modalidad: "todos",
      horario: "",
      direccion: "",
      telefono: "",
      descripcion: "",
    },
    validate: {
      nombre: (v) => (v.trim().length < 1 ? "Nombre requerido" : null),
    },
  });

  async function handleSubmit(values: typeof form.values) {
    setLoading(true);
    try {
      await api.patch("/tenants/me", values);
      notifications.show({
        color: "green",
        title: "Guardado",
        message: isDefault
          ? "Configuración del restaurant actualizada"
          : "Configuración del negocio actualizada",
      });
    } catch {
      notifications.show({
        color: "red",
        title: "Error",
        message: "No se pudo guardar la configuración",
      });
    } finally {
      setLoading(false);
    }
  }

  if (!user) {
    return (
      <SectionCard title={sectionTitle}>
        <Stack gap="xs">
          <Skeleton height={36} />
          <Skeleton height={36} />
        </Stack>
      </SectionCard>
    );
  }

  return (
    <SectionCard title={sectionTitle}>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label={isDefault ? "Nombre del restaurant" : "Nombre del negocio"}
              placeholder="Ej: La Tía Julia Sandwiches"
              radius="md"
              aria-label={isDefault ? "Nombre del restaurant" : "Nombre del negocio"}
              {...form.getInputProps("nombre")}
            />
            {isGastro && (
              <Select
                label="Tipo de cocina"
                placeholder="Selecciona"
                data={TIPO_COCINA_OPTIONS}
                radius="md"
                searchable
                aria-label="Tipo de cocina"
                {...form.getInputProps("tipo_cocina")}
              />
            )}
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Select
              label="Modalidad de atención"
              data={MODALIDAD_OPTIONS}
              radius="md"
              allowDeselect={false}
              aria-label="Modalidad de atención"
              {...form.getInputProps("modalidad")}
            />
            <TextInput
              label="Horario"
              placeholder="Ej: Lun-Sáb 12:00 - 23:00"
              radius="md"
              aria-label="Horario de atención"
              {...form.getInputProps("horario")}
            />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label="Dirección"
              placeholder="Ej: Av. Providencia 1234, Santiago"
              radius="md"
              aria-label={isDefault ? "Dirección del restaurant" : "Dirección del negocio"}
              {...form.getInputProps("direccion")}
            />
            <TextInput
              label="Teléfono"
              placeholder="Ej: +56 9 1234 5678"
              radius="md"
              aria-label="Teléfono de contacto"
              {...form.getInputProps("telefono")}
            />
          </SimpleGrid>

          <Textarea
            label="Descripción"
            placeholder={
              isDefault
                ? "Breve descripción de tu restaurant para la IA (ej: Sandwichería artesanal con posta rosada en pan amasado)"
                : "Breve descripción de tu negocio para la IA…"
            }
            radius="md"
            minRows={2}
            maxRows={4}
            autosize
            aria-label={isDefault ? "Descripción del restaurant" : "Descripción del negocio"}
            {...form.getInputProps("descripcion")}
          />

          <Group justify="flex-end">
            <Button
              type="submit"
              leftSection={<IconDeviceFloppy size={16} />}
              color="indigo"
              radius="md"
              loading={loading}
              aria-label="Guardar configuración"
            >
              Guardar cambios
            </Button>
          </Group>
        </Stack>
      </form>
    </SectionCard>
  );
}
