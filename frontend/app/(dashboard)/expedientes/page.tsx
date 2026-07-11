"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconFolders } from "@tabler/icons-react";

export default function ExpedientesPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Fichas y expedientes"
        subtitle="Historial, documentos adjuntos y notas de evolución."
      />
      <SectionCard>
        <EmptyState
          icon={<IconFolders size={40} />}
          title="En construcción"
          description="Pronto vas a llevar el expediente completo de cada cliente desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
