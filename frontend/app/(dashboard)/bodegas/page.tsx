"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconBuildingWarehouse } from "@tabler/icons-react";

export default function BodegasPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Bodegas y ubicaciones" subtitle="Stock por bodega y ubicación." />
      <SectionCard>
        <EmptyState
          icon={<IconBuildingWarehouse size={40} />}
          title="En construcción"
          description="Pronto vas a organizar tu stock por bodegas y ubicaciones desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
