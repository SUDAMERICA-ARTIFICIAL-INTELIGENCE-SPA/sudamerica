"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconTemplate } from "@tabler/icons-react";

export default function PlantillasPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Plantillas y respuestas rápidas"
        subtitle="Mensajes reutilizables para responder más rápido."
      />
      <SectionCard>
        <EmptyState
          icon={<IconTemplate size={40} />}
          title="En construcción"
          description="Pronto vas a crear y usar plantillas de mensajes desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
