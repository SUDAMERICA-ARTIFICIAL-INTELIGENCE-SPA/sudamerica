"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconFileText } from "@tabler/icons-react";

export default function ContratosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Contratos" subtitle="Contratos vigentes, borradores y vencidos." />
      <SectionCard>
        <EmptyState
          icon={<IconFileText size={40} />}
          title="En construcción"
          description="Pronto vas a crear y seguir contratos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
