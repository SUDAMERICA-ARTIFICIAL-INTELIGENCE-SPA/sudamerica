"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconKey } from "@tabler/icons-react";

export default function ActivosArriendoPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Activos en arriendo" subtitle="Activos arrendados y su estado." />
      <SectionCard>
        <EmptyState
          icon={<IconKey size={40} />}
          title="En construcción"
          description="Pronto vas a administrar los activos en arriendo desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
