"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconChartBar } from "@tabler/icons-react";

export default function CampanasPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Campañas" subtitle="Campañas de difusión y sus resultados." />
      <SectionCard>
        <EmptyState
          icon={<IconChartBar size={40} />}
          title="En construcción"
          description="Pronto vas a lanzar y medir campañas desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
