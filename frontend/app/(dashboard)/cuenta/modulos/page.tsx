"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { useTenant } from "@/hooks/useTenant";
import { CAPACIDADES, CAPACIDADES_META, type CapacidadMeta } from "@/lib/capacidades";
import { Badge, Card, Group, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";

function CapacidadCard({ meta, isActiva }: { meta: CapacidadMeta; isActiva: boolean }) {
  return (
    <Card withBorder radius="md" padding="md" aria-label={`Capacidad ${meta.label}`}>
      <Group justify="space-between" align="flex-start" gap="xs" wrap="nowrap">
        <Text fw={600} size="sm">
          {meta.label}
        </Text>
        <Badge color={isActiva ? "green" : "gray"} variant="light" size="sm">
          {isActiva ? "Activa" : "Disponible"}
        </Badge>
      </Group>
      <Text size="xs" c="dimmed" mt={6}>
        {meta.descripcion}
      </Text>
    </Card>
  );
}

/**
 * Capacidades y módulos — qué puede hacer la cuenta hoy según su rubro.
 * Lee el SSOT de capacidades (lib/capacidades.ts) y las activas del rubro
 * (curadas por rubro en lib/rubros.ts); el plan del servicio viene del tenant.
 */
export default function CapacidadesPage() {
  const rubro = useRubroLabels();
  const { data: tenant } = useTenant();

  if (rubro.isLoading) {
    return (
      <Stack gap="lg">
        <Skeleton height={44} maw={420} radius="md" />
        <Skeleton height={220} radius="lg" />
        <Skeleton height={320} radius="lg" />
      </Stack>
    );
  }

  const activas = new Set(rubro.capacidades);
  const metas = CAPACIDADES.map((slug) => CAPACIDADES_META[slug]);
  const metasActivas = metas.filter((meta) => activas.has(meta.slug));
  const metasDisponibles = metas.filter((meta) => !activas.has(meta.slug));

  return (
    <Stack gap="lg">
      <PageHeader
        title="Capacidades y módulos"
        subtitle={`Lo que tu cuenta puede hacer hoy como ${rubro.nombre}.`}
        actions={
          tenant?.plan ? (
            <Badge variant="light" size="lg" aria-label={`Plan del servicio: ${tenant.plan}`}>
              Plan {tenant.plan}
            </Badge>
          ) : undefined
        }
      />
      <SectionCard
        title={`Activas (${metasActivas.length})`}
        subtitle="Capacidades habilitadas para tu rubro — definen qué secciones ves en el menú."
      >
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {metasActivas.map((meta) => (
            <CapacidadCard key={meta.slug} meta={meta} isActiva />
          ))}
        </SimpleGrid>
      </SectionCard>
      <SectionCard
        title={`Disponibles (${metasDisponibles.length})`}
        subtitle="Capacidades del sistema que tu rubro aún no usa. Escríbenos para activarlas."
      >
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {metasDisponibles.map((meta) => (
            <CapacidadCard key={meta.slug} meta={meta} isActiva={false} />
          ))}
        </SimpleGrid>
      </SectionCard>
    </Stack>
  );
}
