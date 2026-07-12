"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Badge, Breadcrumbs, Group, Skeleton, Stack, Text } from "@mantine/core";
import { IconTool } from "@tabler/icons-react";

export interface StubModuloProps {
  /** Título de la sub (label del SSOT ya renderizado por rubro). */
  title: string;
  /** Categoría del SSOT — contexto en el breadcrumb. */
  categoria: string;
  subtitle?: string;
  /** Vistas anticipadas (badges), opcional. */
  vistas?: readonly string[];
}

/**
 * Placeholder uniforme para toda sub canónica sin página real todavía (Fase 3).
 * Mantine puro, sin lectura de color-scheme en render (evita hydration mismatch):
 * breadcrumb categoría → título, encabezado, y una card con loader coherente + vacío.
 */
export function StubModulo({ title, categoria, subtitle, vistas }: StubModuloProps) {
  return (
    <Stack gap="lg">
      <Breadcrumbs separator="›" aria-label="Ruta de navegación">
        <Text size="sm" c="dimmed">
          {categoria}
        </Text>
        <Text size="sm" fw={500}>
          {title}
        </Text>
      </Breadcrumbs>
      <PageHeader title={title} {...(subtitle ? { subtitle } : {})} />
      <SectionCard>
        <Stack gap="md">
          <Skeleton height={120} radius="md" aria-hidden="true" />
          <Skeleton height={120} radius="md" aria-hidden="true" />
          <EmptyState
            icon={<IconTool size={40} />}
            title="En construcción"
            description={`Pronto vas a gestionar ${title} desde aquí.`}
          />
          {vistas && vistas.length > 0 && (
            <Group gap={6} justify="center">
              {vistas.map((vista) => (
                <Badge key={vista} variant="outline" color="gray" size="sm" radius="sm">
                  {vista}
                </Badge>
              ))}
            </Group>
          )}
        </Stack>
      </SectionCard>
    </Stack>
  );
}
