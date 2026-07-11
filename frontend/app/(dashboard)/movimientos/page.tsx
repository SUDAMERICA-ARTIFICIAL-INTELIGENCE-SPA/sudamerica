"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconTransfer } from "@tabler/icons-react";

export default function MovimientosPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Movimientos de inventario"
        subtitle="Entradas, salidas y ajustes de stock."
      />
      <SectionCard>
        <EmptyState
          icon={<IconTransfer size={40} />}
          title="En construcción"
          description="Pronto vas a registrar y auditar los movimientos de tu inventario desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
