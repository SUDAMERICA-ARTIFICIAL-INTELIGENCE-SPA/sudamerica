"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconClock } from "@tabler/icons-react";

export default function DisponibilidadPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Disponibilidad" subtitle="Horarios, bloqueos y feriados." />
      <SectionCard>
        <EmptyState
          icon={<IconClock size={40} />}
          title="En construcción"
          description="Pronto vas a configurar los horarios y bloqueos de tu agenda desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
