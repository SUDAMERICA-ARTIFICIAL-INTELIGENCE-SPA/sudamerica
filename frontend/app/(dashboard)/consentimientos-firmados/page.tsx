"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconSignature } from "@tabler/icons-react";

export default function ConsentimientosFirmadosPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Consentimientos firmados"
        subtitle="Registro de consentimientos con firma."
      />
      <SectionCard>
        <EmptyState
          icon={<IconSignature size={40} />}
          title="En construcción"
          description="Pronto vas a consultar los consentimientos firmados desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
