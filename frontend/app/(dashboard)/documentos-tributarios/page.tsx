"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconReceipt } from "@tabler/icons-react";

export default function DocumentosTributariosPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Documentos tributarios"
        subtitle="Documentos para tu contabilidad e impuestos."
      />
      <SectionCard>
        <EmptyState
          icon={<IconReceipt size={40} />}
          title="En construcción"
          description="Pronto vas a descargar tus documentos tributarios desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
