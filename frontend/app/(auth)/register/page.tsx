"use client";

export const dynamic = "force-dynamic";

import { useSsrColorScheme } from "@/hooks/useSsrColorScheme";
import { ApiError, useAuth } from "@/lib/auth";
import { RUBRO_DEFAULT } from "@/lib/rubros";
import { useRubrosDisponibles } from "@/hooks/useRubrosDisponibles";
import {
  Alert,
  Anchor,
  Badge,
  Box,
  Button,
  Group,
  PasswordInput,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
  useMantineTheme,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconBike,
  IconClock,
  IconFileUpload,
  IconMapPin,
  IconPhone,
  IconPlus,
  IconRobot,
  IconTruck,
} from "@tabler/icons-react";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useState } from "react";

// ─── Form model & validation ─────────────────────────────────────────────────

interface FormState {
  nombre: string;
  apellido: string;
  email: string;
  tenant_nombre: string;
  rubro: string;
  password: string;
  confirmPassword: string;
}

type FieldErrors = Partial<Record<keyof FormState, string>>;

const EMPTY_FORM: FormState = {
  nombre: "",
  apellido: "",
  email: "",
  tenant_nombre: "",
  rubro: RUBRO_DEFAULT,
  password: "",
  confirmPassword: "",
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Mirrors backend rules: min 8 chars, at least 1 uppercase and 1 digit.
function isValidPassword(value: string): boolean {
  return value.length >= 8 && /[A-Z]/.test(value) && /\d/.test(value);
}

function validate(form: FormState): FieldErrors {
  const errors: FieldErrors = {};
  if (!form.nombre.trim()) errors.nombre = "Ingresa tu nombre";
  if (!form.apellido.trim()) errors.apellido = "Ingresa tu apellido";
  if (!form.email.trim()) errors.email = "Ingresa tu email";
  else if (!EMAIL_RE.test(form.email.trim())) errors.email = "Email no valido";
  if (!form.tenant_nombre.trim()) errors.tenant_nombre = "Ingresa el nombre de tu negocio";
  if (!form.password) errors.password = "Ingresa una contrasena";
  else if (!isValidPassword(form.password))
    errors.password = "Minimo 8 caracteres, 1 mayuscula y 1 numero";
  if (form.confirmPassword !== form.password)
    errors.confirmPassword = "Las contrasenas no coinciden";
  return errors;
}

// ─── Decorative: Delivery Panel ──────────────────────────────────────────────

function DeliveryPanel() {
  // Colores de marca de terceros — identidad visual externa, no tokens propios del design system.
  const deliveryApps = [
    { name: "Uber Eats", color: "#06C167" },
    { name: "Rappi", color: "#FF441F" },
    { name: "PedidosYa", color: "#FA0050" },
    { name: "DoorDash", color: "#FF3008" },
  ];

  return (
    <Box
      bg="surface.0"
      style={{
        border: "1px solid var(--mantine-color-default-border)",
        borderRadius: 16,
        padding: "16px 20px",
      }}
    >
      <Group gap={8} mb={12}>
        <IconBike size={18} />
        <Text fz={13} fw={600}>
          Apps de Delivery
        </Text>
        <Badge size="xs" variant="light" color="amber">
          Proximamente
        </Badge>
      </Group>
      <Stack gap={8}>
        {deliveryApps.map((app) => (
          <Group
            key={app.name}
            gap="sm"
            style={{
              borderRadius: 10,
              padding: "8px 12px",
              border: "1px solid var(--mantine-color-default-border)",
              cursor: "default",
            }}
          >
            <Box
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: app.color,
              }}
            />
            <Text fz={12} c="dimmed" style={{ flex: 1 }}>
              {app.name}
            </Text>
            <IconPhone size={14} color="var(--mantine-color-dimmed)" />
          </Group>
        ))}
      </Stack>
      <Tooltip label="Podras agregar numeros de delivery despues" withArrow>
        <Group
          gap={6}
          mt={10}
          style={{
            cursor: "pointer",
            justifyContent: "center",
            padding: "6px 0",
            borderRadius: 8,
            border: "1px dashed var(--mantine-color-default-border)",
            transition: "all 0.2s",
          }}
        >
          <IconPlus size={14} color="var(--mantine-color-dimmed)" />
          <Text fz={11} c="dimmed">
            Agregar numero
          </Text>
        </Group>
      </Tooltip>
    </Box>
  );
}

// ─── Decorative: PDF Upload Panel ────────────────────────────────────────────

function PdfUploadPanel() {
  return (
    <Tooltip label="Podras subir tu menu en PDF despues del registro" withArrow>
      <Box
        bg="surface.0"
        style={{
          border: "1px dashed var(--mantine-color-default-border)",
          borderRadius: 16,
          padding: "20px",
          textAlign: "center" as const,
          cursor: "default",
          transition: "all 0.2s",
        }}
      >
        <IconFileUpload size={28} color="var(--mantine-color-dimmed)" style={{ marginBottom: 8 }} />
        <Text fz={12} c="dimmed" fw={500}>
          Sube tu menu en PDF
        </Text>
        <Text fz={11} c="dimmed" mt={4}>
          Tu agente IA lo aprendera automaticamente
        </Text>
        <Badge size="xs" variant="light" color="amber" mt={8}>
          Proximamente
        </Badge>
      </Box>
    </Tooltip>
  );
}

// ─── Feature Badges ──────────────────────────────────────────────────────────

function FeatureBadges() {
  const features = [
    { icon: IconRobot, label: "Atencion IA 24/7" },
    { icon: IconTruck, label: "Gestion Delivery" },
    { icon: IconClock, label: "Pedidos Automaticos" },
    { icon: IconMapPin, label: "Calculo de Envio" },
  ];

  return (
    <Group gap={6} justify="center" wrap="wrap">
      {features.map((f) => (
        <Badge
          key={f.label}
          size="sm"
          variant="light"
          color="appleBlue"
          leftSection={<f.icon size={12} />}
        >
          {f.label}
        </Badge>
      ))}
    </Group>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function RegisterPage() {
  const { register } = useAuth();
  const theme = useMantineTheme();
  // SSR-safe (ver hooks/useSsrColorScheme): evita el hydration mismatch del
  // boxShadow inline de la card cuando hay un scheme persistido distinto al default.
  const colorScheme = useSsrColorScheme();
  const cardShadow = colorScheme === "dark" ? theme.other.cardShadowDark : theme.other.cardShadow;
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Set vivo de rubros (incluye runtime creados en la Fase C); baseline estático como fallback.
  const { options: rubroOptions } = useRubrosDisponibles();
  const rubroSelectData = rubroOptions.map((opt) => ({
    value: opt.value,
    label: `${opt.emoji} ${opt.label}`,
  }));

  const setField = useCallback((key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));
  }, []);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (submitting) return;

      const validation = validate(form);
      if (Object.keys(validation).length > 0) {
        setErrors(validation);
        return;
      }

      setSubmitting(true);
      setApiError(null);

      try {
        // register() persists tokens and redirects to /onboarding on success.
        // Omit `rubro` entirely for the default (satisfies exactOptionalPropertyTypes;
        // same wire behavior as an omitted key on JSON.stringify).
        await register({
          nombre: form.nombre.trim(),
          apellido: form.apellido.trim(),
          email: form.email.trim(),
          password: form.password,
          tenant_nombre: form.tenant_nombre.trim(),
          ...(form.rubro && form.rubro !== RUBRO_DEFAULT ? { rubro: form.rubro } : {}),
        });
      } catch (err) {
        let msg = "Error al crear la cuenta. Intenta de nuevo.";
        if (err instanceof ApiError) {
          msg =
            err.status === 409
              ? "Este email ya esta registrado. Inicia sesion o recupera tu contrasena."
              : err.message;
        }
        setApiError(msg);
        setSubmitting(false);
      }
    },
    [form, register, submitting],
  );

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
      {/* Main layout */}
      <Box
        style={{
          display: "flex",
          gap: 20,
          maxWidth: 920,
          width: "100%",
          alignItems: "stretch",
        }}
      >
        {/* ─── Form Panel (Main) ──────────────────────────────── */}
        <Box
          style={{
            flex: "1 1 auto",
            minWidth: 0,
            display: "flex",
            flexDirection: "column" as const,
            background: "var(--mantine-color-body)",
            border: "1px solid var(--mantine-color-default-border)",
            borderRadius: 20,
            boxShadow: cardShadow,
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <Box
            px="lg"
            py="md"
            style={{ borderBottom: "1px solid var(--mantine-color-default-border)" }}
          >
            <Group justify="space-between" align="center" wrap="wrap" gap="xs">
              <Stack gap={2}>
                <Group gap={8} wrap="wrap">
                  <Image
                    src="/logo.png"
                    alt="Sudamérica AI"
                    width={30}
                    height={30}
                    style={{ borderRadius: 6 }}
                  />
                  <Title
                    order={3}
                    fz={22}
                    fw={700}
                    c="light-dark(var(--mantine-color-appleBlue-6), var(--mantine-color-appleBlue-3))"
                    style={{ letterSpacing: "-0.5px" }}
                  >
                    Sudamérica AI
                  </Title>
                  <Badge size="xs" variant="light" color="amber">
                    Restaurantes
                  </Badge>
                </Group>
                <Text fz={12} c="dimmed">
                  Crea tu cuenta para empezar a configurar tu agente IA
                </Text>
              </Stack>
              <Anchor component={Link} href="/login" fz={13} c="dimmed">
                Ya tengo cuenta
              </Anchor>
            </Group>
          </Box>

          {/* Form */}
          <Box component="form" onSubmit={handleSubmit} px="lg" py="lg">
            <Stack gap="md">
              <Group grow gap="md" align="flex-start">
                <TextInput
                  label="Nombre"
                  placeholder="Tu nombre"
                  value={form.nombre}
                  onChange={(e) => setField("nombre", e.currentTarget.value)}
                  error={errors.nombre}
                  disabled={submitting}
                  radius="md"
                  size="md"
                  autoComplete="given-name"
                  aria-label="Nombre"
                />
                <TextInput
                  label="Apellido"
                  placeholder="Tu apellido"
                  value={form.apellido}
                  onChange={(e) => setField("apellido", e.currentTarget.value)}
                  error={errors.apellido}
                  disabled={submitting}
                  radius="md"
                  size="md"
                  autoComplete="family-name"
                  aria-label="Apellido"
                />
              </Group>

              <TextInput
                label="Email"
                placeholder="tu@correo.com"
                type="email"
                value={form.email}
                onChange={(e) => setField("email", e.currentTarget.value)}
                error={errors.email}
                disabled={submitting}
                radius="md"
                size="md"
                autoComplete="email"
                aria-label="Email"
              />

              <TextInput
                label="Nombre del negocio"
                placeholder="Ej: Pizzeria Don Mario"
                value={form.tenant_nombre}
                onChange={(e) => setField("tenant_nombre", e.currentTarget.value)}
                error={errors.tenant_nombre}
                disabled={submitting}
                radius="md"
                size="md"
                autoComplete="organization"
                aria-label="Nombre del negocio"
              />

              <Select
                label="Tipo de negocio"
                placeholder="Elige tu rubro"
                value={form.rubro}
                onChange={(value) => setField("rubro", value ?? "")}
                data={rubroSelectData}
                error={errors.rubro}
                disabled={submitting}
                radius="md"
                size="md"
                aria-label="Tipo de negocio"
              />

              <PasswordInput
                label="Contrasena"
                placeholder="Minimo 8 caracteres, 1 mayuscula y 1 numero"
                value={form.password}
                onChange={(e) => setField("password", e.currentTarget.value)}
                error={errors.password}
                disabled={submitting}
                radius="md"
                size="md"
                autoComplete="new-password"
                aria-label="Contrasena"
              />

              <PasswordInput
                label="Confirmar contrasena"
                placeholder="Repite tu contrasena"
                value={form.confirmPassword}
                onChange={(e) => setField("confirmPassword", e.currentTarget.value)}
                error={errors.confirmPassword}
                disabled={submitting}
                radius="md"
                size="md"
                autoComplete="new-password"
                aria-label="Confirmar contrasena"
              />

              {apiError && (
                <Alert
                  icon={<IconAlertCircle size={16} />}
                  color="red"
                  variant="light"
                  radius="md"
                  aria-live="polite"
                >
                  {apiError}
                </Alert>
              )}

              <Button type="submit" size="md" radius="md" fullWidth mt={4} loading={submitting}>
                {submitting ? "Creando tu cuenta..." : "Crear cuenta"}
              </Button>

              <Text fz={11} c="dimmed" ta="center">
                Despues de crear tu cuenta podras configurar tu carta, tu agente IA y conectar
                WhatsApp.
              </Text>
            </Stack>
          </Box>
        </Box>

        {/* ─── Side Panel (Decorative) ───────────────────────── */}
        <Box
          style={{
            flex: "0 0 280px",
            display: "flex",
            flexDirection: "column" as const,
            gap: 16,
          }}
          visibleFrom="md"
        >
          {/* Feature badges */}
          <FeatureBadges />

          {/* Delivery apps panel */}
          <DeliveryPanel />

          {/* PDF Upload panel */}
          <PdfUploadPanel />

          {/* Stats decorative */}
          <Box
            bg="surface.0"
            style={{
              border: "1px solid var(--mantine-color-default-border)",
              borderRadius: 16,
              padding: "16px 20px",
            }}
          >
            <Text
              fz={11}
              c="dimmed"
              mb={10}
              tt="uppercase"
              fw={600}
              style={{ letterSpacing: "0.5px" }}
            >
              Tu agente IA podra
            </Text>
            <Stack gap={8}>
              {[
                "Tomar pedidos por WhatsApp",
                "Enviar menu con imagenes",
                "Calcular costo de delivery",
                "Generar links de pago",
                "Confirmar pagos automaticamente",
                "Follow-up inteligente",
              ].map((item) => (
                <Group key={item} gap={8}>
                  <Box
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      background: "var(--mantine-color-appleBlue-6)",
                      flexShrink: 0,
                    }}
                  />
                  <Text fz={12} c="dimmed">
                    {item}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
