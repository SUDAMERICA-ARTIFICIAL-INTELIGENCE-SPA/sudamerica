"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/auth";
import { Alert, Button, PasswordInput, Stack } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useState } from "react";

interface PasswordFormValues {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function ChangePasswordCard() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<PasswordFormValues>({
    initialValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
    validate: {
      current_password: (v) => (v.length < 1 ? "Ingresa tu contraseña actual" : null),
      new_password: (v) => {
        if (v.length < 8) return "Minimo 8 caracteres";
        if (!/[A-Z]/.test(v)) return "Debe tener al menos una mayuscula";
        if (!/\d/.test(v)) return "Debe tener al menos un numero";
        return null;
      },
      confirm_password: (v, values) =>
        v !== values.new_password ? "Las contraseñas no coinciden" : null,
    },
  });

  async function handleSubmit(values: PasswordFormValues) {
    setError(null);
    setSuccess(false);
    setLoading(true);
    try {
      await api.post("/auth/change-password", {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      setSuccess(true);
      form.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SectionCard title="Cambiar contraseña">
      {success && (
        <Alert icon={<IconCheck size={16} />} color="green" variant="light" radius="md" mb="md">
          Contraseña actualizada exitosamente.
        </Alert>
      )}
      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light" radius="md" mb="md">
          {error}
        </Alert>
      )}

      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <PasswordInput
            label="Contraseña actual"
            placeholder="Tu contraseña actual"
            autoComplete="current-password"
            aria-label="Contraseña actual"
            {...form.getInputProps("current_password")}
          />
          <PasswordInput
            label="Nueva contraseña"
            placeholder="Minimo 8 caracteres, 1 mayuscula, 1 numero"
            autoComplete="new-password"
            aria-label="Nueva contraseña"
            {...form.getInputProps("new_password")}
          />
          <PasswordInput
            label="Confirmar nueva contraseña"
            placeholder="Repite tu nueva contraseña"
            autoComplete="new-password"
            aria-label="Confirmar nueva contraseña"
            {...form.getInputProps("confirm_password")}
          />
        </Stack>
        <Button
          type="submit"
          mt="md"
          loading={loading}
          disabled={loading}
          color="indigo"
          aria-label="Cambiar contraseña"
        >
          Cambiar contraseña
        </Button>
      </form>
    </SectionCard>
  );
}
