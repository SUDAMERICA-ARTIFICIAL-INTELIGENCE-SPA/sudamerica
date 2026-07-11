"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconFiles } from "@tabler/icons-react";

export default function ArchivosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Archivos" subtitle="Documentos recientes, compartidos y papelera." />
      <SectionCard>
        <EmptyState
          icon={<IconFiles size={40} />}
          title="En construcción"
          description="Pronto vas a guardar y compartir archivos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
