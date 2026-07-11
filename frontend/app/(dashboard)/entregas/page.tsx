"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconTruck } from "@tabler/icons-react";

export default function EntregasPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Entregas" subtitle="Despachos, repartos y su seguimiento." />
      <SectionCard>
        <EmptyState
          icon={<IconTruck size={40} />}
          title="En construcción"
          description="Pronto vas a coordinar y rastrear entregas desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
