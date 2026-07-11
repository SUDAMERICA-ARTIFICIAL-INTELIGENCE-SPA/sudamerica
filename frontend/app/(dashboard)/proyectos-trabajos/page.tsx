"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconLayoutKanban } from "@tabler/icons-react";

export default function ProyectosTrabajosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Proyectos y trabajos" subtitle="Trabajos por fase, hitos y avance." />
      <SectionCard>
        <EmptyState
          icon={<IconLayoutKanban size={40} />}
          title="En construcción"
          description="Pronto vas a seguir tus proyectos por fases e hitos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
