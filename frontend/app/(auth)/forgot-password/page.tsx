"use client";

export const dynamic = "force-dynamic";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/auth";
import { Alert, Anchor, Box, Button, Center, Paper, Stack, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

interface ForgotFormValues {
  email: string;
}

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const form = useForm<ForgotFormValues>({
    initialValues: { email: "" },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Ingresa un email valido"),
    },
  });

  async function handleSubmit(values: ForgotFormValues) {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: values.email }, { skipAuth: true });
      setSent(true);
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
                Recuperar contraseña
              </Text>
            </Stack>

            {sent ? (
              <Alert
                icon={<IconCheck size={16} />}
                color="green"
                variant="light"
                radius="md"
                aria-live="polite"
              >
                Si el email existe en nuestro sistema, recibiras instrucciones para restablecer tu
                contraseña. Revisa tu bandeja de entrada.
              </Alert>
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

                <Text fz={13} c="dimmed" ta="center">
                  Ingresa tu email y te enviaremos un enlace para crear una nueva contraseña.
                </Text>

                <form onSubmit={form.onSubmit(handleSubmit)} noValidate>
                  <Stack gap={16}>
                    <TextInput
                      label="Email"
                      placeholder="tu@empresa.com"
                      type="email"
                      required
                      autoComplete="email"
                      aria-label="Correo electronico"
                      {...form.getInputProps("email")}
                    />
                    <Button
                      type="submit"
                      size="md"
                      fullWidth
                      loading={isLoading}
                      disabled={isLoading}
                      aria-label="Enviar enlace de recuperacion"
                      mt={8}
                    >
                      Enviar enlace
                    </Button>
                  </Stack>
                </form>
              </>
            )}

            <Text fz={13} c="dimmed" ta="center">
              <Anchor component={Link} href="/acceso" fz={13} fw={500}>
                Volver al login
              </Anchor>
            </Text>
          </Stack>
        </Paper>
      </Center>
    </Box>
  );
}
