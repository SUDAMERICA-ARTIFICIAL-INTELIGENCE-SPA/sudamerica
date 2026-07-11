"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconWorld } from "@tabler/icons-react";

export default function CatalogoPublicoPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Catálogo público" subtitle="Tu catálogo visible para clientes." />
      <SectionCard>
        <EmptyState
          icon={<IconWorld size={40} />}
          title="En construcción"
          description="Pronto vas a publicar tu catálogo para clientes desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
