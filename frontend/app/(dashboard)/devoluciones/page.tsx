"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconArrowBackUp } from "@tabler/icons-react";

export default function DevolucionesPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Devoluciones" subtitle="Cambios y devoluciones de pedidos." />
      <SectionCard>
        <EmptyState
          icon={<IconArrowBackUp size={40} />}
          title="En construcción"
          description="Pronto vas a gestionar cambios y devoluciones desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
