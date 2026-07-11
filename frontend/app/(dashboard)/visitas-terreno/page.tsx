"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconMapPin } from "@tabler/icons-react";

export default function VisitasTerrenoPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Visitas en terreno" subtitle="Agenda y rutas de visitas a domicilio." />
      <SectionCard>
        <EmptyState
          icon={<IconMapPin size={40} />}
          title="En construcción"
          description="Pronto vas a programar y seguir visitas en terreno desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
