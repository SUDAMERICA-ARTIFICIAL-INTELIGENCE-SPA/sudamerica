"use client";

import type { CreateLeadDto, UpdateLeadDto } from "@/hooks/useLeads";
import { useUsuarios } from "@/hooks/useUsuarios";
import { LeadCanal } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import { Button, Group, Modal, NumberInput, Select, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect } from "react";

const CANAL_OPTIONS = [
  { value: LeadCanal.WHATSAPP, label: "WhatsApp" },
  { value: LeadCanal.INSTAGRAM, label: "Instagram" },
  { value: LeadCanal.FACEBOOK, label: "Facebook" },
  { value: LeadCanal.WEB, label: "Web" },
  { value: LeadCanal.TELEFONO, label: "Teléfono" },
  { value: LeadCanal.EMAIL, label: "Email" },
  { value: LeadCanal.REFERIDO, label: "Referido" },
];

interface LeadFormValues {
  nombre: string;
  email: string;
  telefono: string;
  canal: string;
  valor_estimado: number | string;
  asesor_id: string;
}

interface LeadFormProps {
  opened: boolean;
  onClose: () => void;
  onSubmit: (dto: CreateLeadDto | UpdateLeadDto) => void;
  isLoading?: boolean;
  lead?: Lead | null;
}

export function LeadForm({ opened, onClose, onSubmit, isLoading, lead }: LeadFormProps) {
  const { data: usuarios } = useUsuarios();
  const isEdit = !!lead;

  const form = useForm<LeadFormValues>({
    initialValues: {
      nombre: "",
      email: "",
      telefono: "",
      canal: LeadCanal.WHATSAPP,
      valor_estimado: "",
      asesor_id: "",
    },
    validate: {
      nombre: (v) => (v.trim().length < 2 ? "Mínimo 2 caracteres" : null),
      canal: (v) => (v ? null : "Selecciona un canal"),
      email: (v) => (v && !/^[^@]+@[^@]+\.[^@]+$/.test(v) ? "Email inválido" : null),
    },
  });

  // Populate form when editing
  useEffect(() => {
    if (lead) {
      form.setValues({
        nombre: lead.nombre,
        email: lead.email ?? "",
        telefono: lead.telefono ?? "",
        canal: lead.canal,
        valor_estimado: lead.valor_estimado ?? "",
        asesor_id: lead.asesor_id ?? "",
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lead, opened]);

  function handleSubmit(values: LeadFormValues) {
    const dto: CreateLeadDto = {
      nombre: values.nombre.trim(),
      canal: values.canal as LeadCanal,
      ...(values.email ? { email: values.email.trim() } : {}),
      ...(values.telefono ? { telefono: values.telefono.trim() } : {}),
      ...(values.valor_estimado !== "" ? { valor_estimado: Number(values.valor_estimado) } : {}),
      ...(values.asesor_id ? { asesor_id: values.asesor_id } : {}),
    };
    onSubmit(dto);
  }

  const asesorOptions =
    usuarios?.map((u) => ({ value: u.id, label: `${u.nombre} (${u.role})` })) ?? [];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? "Editar Cliente" : "Nuevo Cliente"}
      size="md"
      radius="md"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            label="Nombre"
            placeholder="Nombre del cliente"
            required
            aria-label="Nombre del cliente"
            radius="md"
            {...form.getInputProps("nombre")}
          />

          <Group grow gap="sm">
            <TextInput
              label="Email"
              placeholder="email@ejemplo.com"
              type="email"
              aria-label="Email del cliente"
              radius="md"
              {...form.getInputProps("email")}
            />
            <TextInput
              label="Teléfono"
              placeholder="+54 11 1234-5678"
              aria-label="Teléfono del cliente"
              radius="md"
              {...form.getInputProps("telefono")}
            />
          </Group>

          <Select
            label="Canal de captación"
            placeholder="Selecciona el canal"
            data={CANAL_OPTIONS}
            required
            aria-label="Canal de captación del cliente"
            radius="md"
            {...form.getInputProps("canal")}
          />

          <Group grow gap="sm">
            <NumberInput
              label="Valor estimado (USD)"
              placeholder="0"
              min={0}
              prefix="$"
              aria-label="Valor estimado de la oportunidad"
              radius="md"
              {...form.getInputProps("valor_estimado")}
            />
            <Select
              label="Asesor asignado"
              placeholder="Sin asignar"
              data={asesorOptions}
              clearable
              aria-label="Asesor asignado al cliente"
              radius="md"
              {...form.getInputProps("asesor_id")}
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
              aria-label={isEdit ? "Guardar cambios" : "Crear cliente"}
            >
              {isEdit ? "Guardar cambios" : "Crear Cliente"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
