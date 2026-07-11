"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconAward } from "@tabler/icons-react";

export default function PlanesMembresiasPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Planes y membresías"
        subtitle="Planes recurrentes y beneficios para tus clientes."
      />
      <SectionCard>
        <EmptyState
          icon={<IconAward size={40} />}
          title="En construcción"
          description="Pronto vas a definir planes y membresías desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
