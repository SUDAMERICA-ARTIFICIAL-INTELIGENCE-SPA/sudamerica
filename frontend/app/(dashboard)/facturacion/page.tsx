"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconReceipt2 } from "@tabler/icons-react";

export default function FacturacionPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Facturación" subtitle="Boletas y facturas emitidas." />
      <SectionCard>
        <EmptyState
          icon={<IconReceipt2 size={40} />}
          title="En construcción"
          description="Pronto vas a emitir y consultar tus documentos de venta desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
