"use client";

import { ApiError, useAuth } from "@/lib/auth";
import {
  Anchor,
  Button,
  Group,
  PasswordInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconArrowRight } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import type { OnboardingStepProps } from "./shared";

const DRAFT_KEY = "onboarding_cuenta_draft";

interface CuentaForm {
  nombre: string;
  apellido: string;
  tenant_nombre: string;
  email: string;
  password: string;
}

/** Campos persistibles del draft (nunca la contraseña). */
type CuentaDraft = Omit<CuentaForm, "password">;

function readDraft(): Partial<CuentaDraft> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    return raw ? (JSON.parse(raw) as Partial<CuentaDraft>) : {};
  } catch {
    return {};
  }
}

export function StepCuenta({ goNext }: OnboardingStepProps) {
  const { register } = useAuth();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<CuentaForm>({
    initialValues: {
      nombre: "",
      apellido: "",
      tenant_nombre: "",
      email: "",
      password: "",
      ...readDraft(),
    },
    validate: {
      nombre: (v) => (v.trim().length < 1 ? "Ingresa tu nombre" : null),
      apellido: (v) => (v.trim().length < 1 ? "Ingresa tu apellido" : null),
      tenant_nombre: (v) => (v.trim().length < 1 ? "Ingresa el nombre del negocio" : null),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Email inválido"),
      password: (v) => {
        if (v.length < 8) return "Mínimo 8 caracteres";
        if (!/[A-Z]/.test(v)) return "Incluye al menos una mayúscula";
        if (!/\d/.test(v)) return "Incluye al menos un número";
        return null;
      },
    },
  });

  // Espeja el draft (sin contraseña) para no perder lo tipeado si se recarga la página.
  useEffect(() => {
    const { nombre, apellido, tenant_nombre, email } = form.values;
    const draft: CuentaDraft = { nombre, apellido, tenant_nombre, email };
    try {
      window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch {
      // localStorage no disponible: el draft es best-effort.
    }
  }, [form.values]);

  async function handleSubmit(values: CuentaForm) {
    setSubmitting(true);
    try {
      // El rubro se elige en el paso siguiente (pantalla dedicada), no aquí.
      await register({
        email: values.email.trim(),
        password: values.password,
        nombre: values.nombre.trim(),
        apellido: values.apellido.trim(),
        tenant_nombre: values.tenant_nombre.trim(),
      });
      try {
        window.localStorage.removeItem(DRAFT_KEY);
      } catch {
        // best-effort
      }
      goNext();
    } catch (error) {
      const message =
        error instanceof ApiError && error.status === 409
          ? "Ya existe una cuenta con este email."
          : error instanceof Error
            ? error.message
            : "No se pudo crear la cuenta.";
      form.setFieldError("email", message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <Text c="dimmed" size="sm">
          Creamos tu cuenta y tu negocio. Después descubrimos tu rubro y dejamos todo listo.
        </Text>

        <TextInput
          label="Nombre del negocio"
          placeholder="Ej: Panadería La Espiga"
          withAsterisk
          {...form.getInputProps("tenant_nombre")}
        />

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <TextInput label="Tu nombre" withAsterisk {...form.getInputProps("nombre")} />
          <TextInput label="Tu apellido" withAsterisk {...form.getInputProps("apellido")} />
        </SimpleGrid>

        <TextInput
          label="Email"
          placeholder="tu@negocio.com"
          type="email"
          autoComplete="email"
          withAsterisk
          {...form.getInputProps("email")}
        />

        <PasswordInput
          label="Contraseña"
          description="Mínimo 8 caracteres, con una mayúscula y un número."
          autoComplete="new-password"
          withAsterisk
          {...form.getInputProps("password")}
        />

        <Group justify="space-between" mt="xs">
          <Text size="sm" c="dimmed">
            ¿Ya tienes cuenta?{" "}
            <Anchor href="/acceso" size="sm">
              Inicia sesión
            </Anchor>
          </Text>
          <Button type="submit" loading={submitting} rightSection={<IconArrowRight size={16} />}>
            Crear cuenta y continuar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
