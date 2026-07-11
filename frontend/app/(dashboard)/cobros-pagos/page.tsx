"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconCash } from "@tabler/icons-react";

export default function CobrosPagosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Cobros y pagos" subtitle="Cobros pendientes, pagados y vencidos." />
      <SectionCard>
        <EmptyState
          icon={<IconCash size={40} />}
          title="En construcción"
          description="Pronto vas a cobrar y conciliar pagos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
