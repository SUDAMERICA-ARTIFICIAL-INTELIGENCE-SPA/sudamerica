"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconCalendarStats } from "@tabler/icons-react";

export default function DisponibilidadActivosPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Disponibilidad de activos"
        subtitle="Calendario de ocupación de tus activos."
      />
      <SectionCard>
        <EmptyState
          icon={<IconCalendarStats size={40} />}
          title="En construcción"
          description="Pronto vas a ver la ocupación y disponibilidad de tus activos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
