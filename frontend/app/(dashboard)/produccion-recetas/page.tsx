"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconToolsKitchen2 } from "@tabler/icons-react";

export default function ProduccionRecetasPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Producción y recetas"
        subtitle="Recetas, insumos y órdenes de producción."
      />
      <SectionCard>
        <EmptyState
          icon={<IconToolsKitchen2 size={40} />}
          title="En construcción"
          description="Pronto vas a controlar producción y recetas desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
