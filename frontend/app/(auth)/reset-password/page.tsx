"use client";

export const dynamic = "force-dynamic";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/auth";
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
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

interface ResetFormValues {
  new_password: string;
  confirm_password: string;
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const form = useForm<ResetFormValues>({
    initialValues: { new_password: "", confirm_password: "" },
    validate: {
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

  async function handleSubmit(values: ResetFormValues) {
    if (!token) {
      setErrorMessage("Token no encontrado. Solicita un nuevo enlace.");
      return;
    }
    setErrorMessage(null);
    setIsLoading(true);
    try {
      await api.post(
        "/auth/reset-password",
        { token, new_password: values.new_password },
        { skipAuth: true },
      );
      setSuccess(true);
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
          Nueva contraseña
        </Text>
      </Stack>

      {success ? (
        <>
          <Alert
            icon={<IconCheck size={16} />}
            color="green"
            variant="light"
            radius="md"
            aria-live="polite"
          >
            Contraseña actualizada exitosamente. Ya puedes iniciar sesion.
          </Alert>
          <Button
            component={Link}
            href="/login"
            fullWidth
            size="md"
            variant="light"
            aria-label="Ir al login"
          >
            Ir al login
          </Button>
        </>
      ) : (
        <>
          {errorMessage && (
            <Alert
              icon={<IconAlertCircle size={16} />}
              color="red"
              variant="light"
              radius="md"
              aria-live="polite"
            >
              {errorMessage}
            </Alert>
          )}

          {!token && (
            <Alert color="yellow" variant="light" radius="md">
              Enlace invalido. Solicita un nuevo enlace desde{" "}
              <Anchor component={Link} href="/forgot-password" fz={13}>
                aqui
              </Anchor>
              .
            </Alert>
          )}

          <form onSubmit={form.onSubmit(handleSubmit)} noValidate>
            <Stack gap={16}>
              <PasswordInput
                label="Nueva contraseña"
                placeholder="Minimo 8 caracteres, 1 mayuscula, 1 numero"
                required
                autoComplete="new-password"
                aria-label="Nueva contraseña"
                {...form.getInputProps("new_password")}
              />
              <PasswordInput
                label="Confirmar contraseña"
                placeholder="Repite tu nueva contraseña"
                required
                autoComplete="new-password"
                aria-label="Confirmar contraseña"
                {...form.getInputProps("confirm_password")}
              />
              <Button
                type="submit"
                size="md"
                fullWidth
                loading={isLoading}
                disabled={isLoading || !token}
                aria-label="Actualizar contraseña"
                mt={8}
              >
                Actualizar contraseña
              </Button>
            </Stack>
          </form>
        </>
      )}

      <Text fz={13} c="dimmed" ta="center">
        <Anchor component={Link} href="/login" fz={13} fw={500}>
          Volver al login
        </Anchor>
      </Text>
    </Stack>
  );
}

export default function ResetPasswordPage() {
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
          <Suspense fallback={null}>
            <ResetPasswordForm />
          </Suspense>
        </Paper>
      </Center>
    </Box>
  );
}
