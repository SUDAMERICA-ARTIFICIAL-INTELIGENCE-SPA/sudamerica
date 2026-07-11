"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconSignature } from "@tabler/icons-react";

export default function ConsentimientosPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Consentimientos" subtitle="Autorizaciones y permisos de tus contactos." />
      <SectionCard>
        <EmptyState
          icon={<IconSignature size={40} />}
          title="En construcción"
          description="Pronto vas a solicitar y registrar consentimientos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
