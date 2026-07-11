"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconNotebook } from "@tabler/icons-react";

export default function CursosProgramasPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Cursos y programas"
        subtitle="Programas con sesiones, cupos e inscritos."
      />
      <SectionCard>
        <EmptyState
          icon={<IconNotebook size={40} />}
          title="En construcción"
          description="Pronto vas a administrar cursos y programas desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
