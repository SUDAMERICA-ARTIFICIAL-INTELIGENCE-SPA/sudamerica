"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconFolderOpen } from "@tabler/icons-react";

export default function ExpedientesCasosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Expedientes y casos" subtitle="Carpetas por cliente o caso." />
      <SectionCard>
        <EmptyState
          icon={<IconFolderOpen size={40} />}
          title="En construcción"
          description="Pronto vas a ordenar expedientes y casos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
