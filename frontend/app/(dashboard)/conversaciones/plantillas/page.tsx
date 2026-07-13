"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { usePlantillas } from "@/hooks/useOlab";
import { Badge, Card, Code, Group, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";
import { IconTemplate } from "@tabler/icons-react";

const CANAL_FALLBACK = "gray";
const CANAL_COLOR: Record<string, string> = {
  WHATSAPP: "green",
  INSTAGRAM: "grape",
  EMAIL: "blue",
  WEB: "indigo",
  SMS: "cyan",
};

export default function Page() {
  const { data, isLoading } = usePlantillas({ page_size: 100 });
  const plantillas = data?.data ?? [];

  return (
    <Stack gap="lg">
      <PageHeader title="Plantillas" subtitle="Mensajes reutilizables para tus canales de comunicación" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <KpiCard title="Plantillas" value={data?.meta.total ?? 0} isLoading={isLoading} icon={<IconTemplate size={18} />} />
      </SimpleGrid>

      <SectionCard title="Biblioteca de plantillas">
        {isLoading ? (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} height={160} radius="md" />)}
          </SimpleGrid>
        ) : plantillas.length === 0 ? (
          <EmptyState icon={<IconTemplate size={40} />} title="Sin plantillas" description="Aún no hay plantillas de mensajes configuradas." />
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            {plantillas.map((p) => (
              <Card key={p.id} withBorder radius="md" padding="lg">
                <Stack gap="sm">
                  <Group justify="space-between" align="flex-start">
                    <Text fw={600}>{p.nombre}</Text>
                    <Group gap="xs">
                      <Badge variant="light" color={CANAL_COLOR[p.canal] ?? CANAL_FALLBACK} radius="sm">{p.canal}</Badge>
                      {p.categoria && <Badge variant="outline" color="gray" radius="sm">{p.categoria}</Badge>}
                    </Group>
                  </Group>
                  <Code block>{p.contenido}</Code>
                  {p.variables.length > 0 && (
                    <Group gap="xs">
                      {p.variables.map((v) => (
                        <Badge key={v} variant="dot" color="teal" radius="sm" size="sm">{v}</Badge>
                      ))}
                    </Group>
                  )}
                  <Text size="xs" c="dimmed">{p.usos} usos</Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </SectionCard>
    </Stack>
  );
}
