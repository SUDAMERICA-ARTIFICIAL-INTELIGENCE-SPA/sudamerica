"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconHeart } from "@tabler/icons-react";

export default function ProgramaFidelizacionPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Programa de fidelización"
        subtitle="Puntos, premios y clientes frecuentes."
      />
      <SectionCard>
        <EmptyState
          icon={<IconHeart size={40} />}
          title="En construcción"
          description="Pronto vas a premiar a tus clientes frecuentes desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
