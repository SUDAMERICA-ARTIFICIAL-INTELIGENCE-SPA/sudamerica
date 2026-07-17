"use client";

import { useAuth } from "@/lib/auth";
import { ACCENT, DARK, GLASS, SHADOWS_DARK } from "@/lib/theme-tokens";
import {
  Anchor,
  Box,
  Button,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";

/** Convierte un color del design system (#RRGGBB) a rgba con alpha custom. */
function withAlpha(hex: string, alpha: number): string {
  const r = Number.parseInt(hex.slice(1, 3), 16);
  const g = Number.parseInt(hex.slice(3, 5), 16);
  const b = Number.parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function LoginPage() {
  const { login } = useAuth();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Email inválido"),
      password: (v) => (v.length < 1 ? "Ingresa tu contraseña" : null),
    },
  });

  async function handleSubmit(values: { email: string; password: string }) {
    setSubmitting(true);
    try {
      await login({ email: values.email.trim(), password: values.password });
      // login() redirige a /dashboard en caso de éxito.
    } catch (error) {
      form.setFieldError(
        "password",
        error instanceof Error ? error.message : "No se pudo iniciar sesión.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 16px",
        background: `radial-gradient(circle at 50% -10%, ${withAlpha(ACCENT, 0.22)}, transparent 45%), linear-gradient(160deg, ${DARK.background} 0%, ${DARK.surface} 55%, ${DARK.background} 100%)`,
      }}
    >
      <Paper
        w="100%"
        maw={420}
        radius="xl"
        p={0}
        style={{
          overflow: "hidden",
          background: GLASS.dark.background,
          backdropFilter: GLASS.dark.backdropFilter,
          border: `1px solid ${DARK.hairline}`,
          boxShadow: SHADOWS_DARK.xl,
        }}
      >
        <Box style={{ height: 4, background: "var(--sudamerica-gradient)" }} />
        <Box p="xl">
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack gap="md">
              <Stack gap={2}>
                <Title order={2} c="white">
                  Inicia sesión
                </Title>
                <Text c="dimmed" size="sm">
                  Bienvenido de vuelta a Sudamérica AI.
                </Text>
              </Stack>

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
                autoComplete="current-password"
                withAsterisk
                {...form.getInputProps("password")}
              />

              <Button type="submit" loading={submitting} fullWidth mt="xs">
                Entrar
              </Button>

              <Group justify="center" gap={4}>
                <Text size="sm" c="dimmed">
                  ¿No tienes cuenta?
                </Text>
                <Anchor href="/registro" size="sm">
                  Crea tu negocio
                </Anchor>
              </Group>
              <Group justify="center">
                <Anchor href="/forgot-password" size="xs" c="dimmed">
                  Olvidé mi contraseña
                </Anchor>
              </Group>
            </Stack>
          </form>
        </Box>
      </Paper>
    </Box>
  );
}
