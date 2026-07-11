"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconFileInvoice } from "@tabler/icons-react";

export default function CotizacionesPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Cotizaciones" subtitle="Borradores, enviadas y aprobadas." />
      <SectionCard>
        <EmptyState
          icon={<IconFileInvoice size={40} />}
          title="En construcción"
          description="Pronto vas a crear presupuestos y seguir su aprobación desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
