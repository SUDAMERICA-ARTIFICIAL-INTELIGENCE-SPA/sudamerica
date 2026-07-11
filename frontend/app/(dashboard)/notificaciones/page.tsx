"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconBell } from "@tabler/icons-react";

export default function NotificacionesPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Notificaciones" subtitle="Avisos del sistema, de la IA y de tu equipo." />
      <SectionCard>
        <EmptyState
          icon={<IconBell size={40} />}
          title="En construcción"
          description="Pronto vas a revisar y administrar todos tus avisos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
