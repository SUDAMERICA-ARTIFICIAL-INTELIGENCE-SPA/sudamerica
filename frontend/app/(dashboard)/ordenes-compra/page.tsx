"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconShoppingCart } from "@tabler/icons-react";

export default function OrdenesCompraPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Órdenes de compra"
        subtitle="Borradores, enviadas y recepción de mercadería."
      />
      <SectionCard>
        <EmptyState
          icon={<IconShoppingCart size={40} />}
          title="En construcción"
          description="Pronto vas a comprar a proveedores y recibir mercadería desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
