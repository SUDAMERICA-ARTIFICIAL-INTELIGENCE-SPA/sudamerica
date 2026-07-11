"use client";

import { useAuth } from "@/lib/auth";
import {
  Box,
  Button,
  Card,
  Center,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
      return "Email o contraseña incorrectos";
    case "auth/too-many-requests":
      return "Demasiados intentos. Intenta más tarde";
    case "auth/user-disabled":
      return "Cuenta deshabilitada";
    default:
      return "Error de autenticación";
  }
}

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, router]);

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (!v.includes("@") ? "Email inválido" : null),
      password: (v) => (v.length < 1 ? "Contraseña requerida" : null),
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitting(true);
    try {
      await login(values);
    } catch (err: unknown) {
      const error = err as { code?: string; message?: string };
      const message = error.code
        ? getFirebaseErrorMessage(error.code)
        : error.message || "Error desconocido";
      notifications.show({
        color: "red",
        title: "Error de acceso",
        message,
      });
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <Center h="100vh" bg="gray.1">
      <Card w={420} p="xl" shadow="md" radius="lg">
        <Stack gap="md">
          <Box ta="center">
            <Title order={2}>Sudamerica Admin</Title>
            <Text c="dimmed" size="sm">
              Panel de administración — Sudamérica AI
            </Text>
          </Box>

          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <TextInput
                label="Email"
                placeholder="admin@sudamerica.ai"
                {...form.getInputProps("email")}
              />
              <PasswordInput
                label="Contraseña"
                placeholder="••••••••"
                {...form.getInputProps("password")}
              />
              <Button type="submit" fullWidth mt="sm" loading={submitting}>
                Iniciar sesión
              </Button>
            </Stack>
          </form>

          <Text c="dimmed" size="xs" ta="center">
            Acceso restringido a @sudamerica.ai
          </Text>
        </Stack>
      </Card>
    </Center>
  );
}
