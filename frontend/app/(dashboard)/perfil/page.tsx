"use client";

import { ChangePasswordCard } from "@/components/configuracion/ChangePasswordCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/auth";
import { useAuth } from "@/lib/auth";
import { USER_ROLE_COLORS, USER_ROLE_LABELS } from "@/lib/enums";
import type { Usuario } from "@/lib/types";
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useState } from "react";

function getInitials(nombre: string, apellido?: string): string {
  const first = nombre?.[0]?.toUpperCase() ?? "";
  const last = apellido?.[0]?.toUpperCase() ?? "";
  return `${first}${last}`;
}

interface ProfileFormValues {
  nombre: string;
  apellido: string;
}

export default function PerfilPage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <Box p="md">
      <Stack gap="lg">
        <PageHeader title="Mi Perfil" />

        <Grid gutter="lg">
          {/* Profile card */}
          <Grid.Col span={{ base: 12, md: 4 }}>
            <ProfileCard user={user} />
          </Grid.Col>

          {/* Edit profile + change password */}
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Stack gap="lg">
              <EditProfileCard user={user} />
              <ChangePasswordCard />
              <EmailVerificationCard user={user} />
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </Box>
  );
}

function ProfileCard({ user }: { user: Usuario }) {
  return (
    <Card radius="md" shadow="sm" padding="xl" withBorder>
      <Stack align="center" gap="md">
        <Avatar
          size={80}
          radius="xl"
          color="indigo"
          style={{
            boxShadow:
              "0 0 0 3px var(--mantine-color-body), 0 0 0 5px var(--mantine-color-indigo-5)",
          }}
        >
          <Text fz={28} fw={700}>
            {getInitials(user.nombre, user.apellido)}
          </Text>
        </Avatar>
        <Stack gap={4} align="center">
          <Text fz="lg" fw={700}>
            {user.nombre} {user.apellido}
          </Text>
          <Text fz="sm" c="dimmed">
            {user.email}
          </Text>
          <Badge variant="light" color={USER_ROLE_COLORS[user.role] ?? "gray"} size="md">
            {USER_ROLE_LABELS[user.role] ?? user.role}
          </Badge>
        </Stack>
        <Divider w="100%" />
        <Stack gap={4} w="100%">
          <Group justify="space-between">
            <Text fz="xs" c="dimmed">
              Email verificado
            </Text>
            <Badge size="sm" variant="light" color={user.email_verified ? "green" : "yellow"}>
              {user.email_verified ? "Si" : "Pendiente"}
            </Badge>
          </Group>
          <Group justify="space-between">
            <Text fz="xs" c="dimmed">
              Miembro desde
            </Text>
            <Text fz="xs">{new Date(user.created_at).toLocaleDateString("es-CL")}</Text>
          </Group>
        </Stack>
      </Stack>
    </Card>
  );
}

function EditProfileCard({ user }: { user: Usuario }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<ProfileFormValues>({
    initialValues: {
      nombre: user.nombre,
      apellido: user.apellido,
    },
    validate: {
      nombre: (v) => (v.trim().length < 1 ? "Nombre requerido" : null),
    },
  });

  async function handleSubmit(values: ProfileFormValues) {
    setError(null);
    setSuccess(false);
    setLoading(true);
    try {
      await api.patch("/auth/profile", values);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SectionCard title="Datos personales">
      {success && (
        <Alert icon={<IconCheck size={16} />} color="green" variant="light" radius="md" mb="md">
          Perfil actualizado exitosamente.
        </Alert>
      )}
      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light" radius="md" mb="md">
          {error}
        </Alert>
      )}

      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Grid gutter="md">
          <Grid.Col span={6}>
            <TextInput
              label="Nombre"
              placeholder="Tu nombre"
              aria-label="Nombre"
              {...form.getInputProps("nombre")}
            />
          </Grid.Col>
          <Grid.Col span={6}>
            <TextInput
              label="Apellido"
              placeholder="Tu apellido"
              aria-label="Apellido"
              {...form.getInputProps("apellido")}
            />
          </Grid.Col>
          <Grid.Col span={12}>
            <TextInput label="Email" value={user.email} disabled aria-label="Email (no editable)" />
          </Grid.Col>
        </Grid>
        <Button
          type="submit"
          mt="md"
          loading={loading}
          disabled={loading}
          aria-label="Guardar cambios"
        >
          Guardar cambios
        </Button>
      </form>
    </SectionCard>
  );
}

function EmailVerificationCard({ user }: { user: Usuario }) {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user.email_verified) return null;

  async function handleResend() {
    setError(null);
    setSent(false);
    setLoading(true);
    try {
      await api.post("/auth/resend-verification");
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SectionCard title="Verificacion de email">
      <Alert color="yellow" variant="light" radius="md" mb="md">
        Tu email aun no ha sido verificado. Verifica tu email para acceder a todas las funciones.
      </Alert>

      {sent && (
        <Alert icon={<IconCheck size={16} />} color="green" variant="light" radius="md" mb="md">
          Email de verificacion enviado. Revisa tu bandeja de entrada.
        </Alert>
      )}
      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light" radius="md" mb="md">
          {error}
        </Alert>
      )}

      <Button
        onClick={handleResend}
        loading={loading}
        disabled={loading || sent}
        variant="light"
        aria-label="Reenviar verificacion"
      >
        {sent ? "Email enviado" : "Reenviar email de verificacion"}
      </Button>
    </SectionCard>
  );
}
