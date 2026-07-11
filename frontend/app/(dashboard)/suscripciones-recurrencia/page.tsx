"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconRepeat } from "@tabler/icons-react";

export default function SuscripcionesRecurrenciaPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Suscripciones y recurrencia"
        subtitle="Ingresos recurrentes y renovaciones."
      />
      <SectionCard>
        <EmptyState
          icon={<IconRepeat size={40} />}
          title="En construcción"
          description="Pronto vas a administrar suscripciones y renovaciones desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
