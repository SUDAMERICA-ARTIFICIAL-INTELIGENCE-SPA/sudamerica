"use client";

export const dynamic = "force-dynamic";

import { ApiError, useAuth } from "@/lib/auth";
import {
  Alert,
  Anchor,
  Box,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertCircle } from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

interface LoginFormValues {
  email: string;
  password: string;
}

export default function LoginPage() {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Ingresa un email válido"),
      password: (v) => (v.length >= 6 ? null : "Mínimo 6 caracteres"),
    },
  });

  async function handleSubmit(values: LoginFormValues) {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      await login({ email: values.email, password: values.password });
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Error inesperado. Intenta de nuevo.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Box
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <Center style={{ width: "100%" }}>
        <Paper radius="lg" p={40} w="100%" maw={420} shadow="sm" withBorder>
          <Stack gap={24}>
            <Stack gap={6} align="center">
              <Image
                src="/logo.png"
                alt="Sudamérica AI"
                width={56}
                height={56}
                priority
                style={{ borderRadius: 12 }}
              />
              <Text
                fz={28}
                fw={800}
                c="light-dark(var(--mantine-color-appleBlue-6), var(--mantine-color-appleBlue-3))"
                style={{ letterSpacing: "-0.5px", lineHeight: 1 }}
              >
                Sudamérica AI
              </Text>
              <Text fz={14} c="dimmed" ta="center">
                Gastronomia inteligente
              </Text>
            </Stack>

            {errorMessage && (
              <Alert
                icon={<IconAlertCircle size={16} />}
                color="red"
                variant="light"
                radius="md"
                aria-live="polite"
                aria-label="Error de autenticación"
              >
                {errorMessage}
              </Alert>
            )}

            <form onSubmit={form.onSubmit(handleSubmit)} noValidate>
              <Stack gap={16}>
                <TextInput
                  label="Email"
                  placeholder="tu@empresa.com"
                  type="email"
                  required
                  autoComplete="email"
                  aria-label="Correo electrónico"
                  {...form.getInputProps("email")}
                />
                <PasswordInput
                  label="Contraseña"
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  aria-label="Contraseña"
                  {...form.getInputProps("password")}
                />
                <Text fz={12} ta="right" mt={-8}>
                  <Anchor component={Link} href="/forgot-password" fz={12} c="dimmed">
                    ¿Olvidaste tu contraseña?
                  </Anchor>
                </Text>
                <Button
                  type="submit"
                  size="md"
                  fullWidth
                  loading={isLoading}
                  disabled={isLoading}
                  aria-label="Iniciar sesion"
                  mt={8}
                >
                  Iniciar sesion
                </Button>
              </Stack>
            </form>

            <Text fz={13} c="dimmed" ta="center">
              ¿No tienes cuenta?{" "}
              <Anchor component={Link} href="/register" fz={13} fw={500}>
                Regístrate gratis
              </Anchor>
            </Text>
          </Stack>
        </Paper>
      </Center>
    </Box>
  );
}
