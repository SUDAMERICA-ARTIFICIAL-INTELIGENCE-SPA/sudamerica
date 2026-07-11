"use client";

import DashboardContent from "@/app/(dashboard)/dashboard/page";
import { setDemoRubro } from "@/lib/demo/state";
import { type RubroDef, getRubroDef, resolveRubro, rubroSectorConfig } from "@/lib/rubros";
import { Badge, Container, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

function makeDemoClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: Number.POSITIVE_INFINITY },
    },
  });
}

function RubroDashboard({ def }: { def: RubroDef }) {
  // Fija el rubro activo antes de que los hooks disparen sus queries; el resolver
  // lo lee al ejecutar la queryFn (post-commit). Determinista e idempotente.
  setDemoRubro(def.key);
  const [queryClient] = useState(makeDemoClient);
  const sector = rubroSectorConfig(def.key);

  return (
    <QueryClientProvider client={queryClient}>
      <Container size="xl" py="md">
        <Stack gap="lg">
          <Group justify="space-between" align="center" wrap="wrap" gap="sm">
            <Group gap="sm" align="center" wrap="nowrap">
              <Text style={{ fontSize: 30, lineHeight: 1 }} aria-hidden>
                {def.emoji}
              </Text>
              <Stack gap={2}>
                <Text fw={700} size="lg">
                  {def.nombre}
                </Text>
                <Badge variant="light" color="grape" radius="sm" size="sm">
                  {sector.label}
                </Badge>
              </Stack>
            </Group>
            <Text
              component={Link}
              href="/showroom"
              size="sm"
              c="indigo"
              fw={600}
              aria-label="Volver a todas las cuentas del showroom"
            >
              <Group gap={4} align="center" wrap="nowrap">
                <ThemeIcon variant="subtle" color="indigo" size="sm" aria-hidden>
                  <IconArrowLeft size={16} />
                </ThemeIcon>
                Todos los rubros
              </Group>
            </Text>
          </Group>

          <DashboardContent />
        </Stack>
      </Container>
    </QueryClientProvider>
  );
}

// Dashboard demo de un rubro (`/showroom/<key>`). Reutiliza el dashboard real
// (mismos componentes → misma estética). `key` fuerza remount al cambiar de
// rubro → QueryClient nuevo (cache limpio) → refetch con el rubro correcto.
export default function ShowroomRubroPage() {
  const params = useParams<{ rubro: string }>();
  const def = getRubroDef(resolveRubro({ rubro: params.rubro }));
  return <RubroDashboard def={def} key={def.key} />;
}
