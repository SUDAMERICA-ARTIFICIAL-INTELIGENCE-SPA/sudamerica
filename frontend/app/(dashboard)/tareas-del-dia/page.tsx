"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconChecklist } from "@tabler/icons-react";

export default function TareasDelDiaPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Tareas del día" subtitle="Pendientes y seguimientos priorizados de hoy." />
      <SectionCard>
        <EmptyState
          icon={<IconChecklist size={40} />}
          title="En construcción"
          description="Pronto vas a organizar los pendientes del día de tu negocio desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
