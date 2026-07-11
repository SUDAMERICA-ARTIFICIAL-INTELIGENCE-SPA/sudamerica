"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconTicket } from "@tabler/icons-react";

export default function TicketsPage() {
  return (
    <Stack gap="lg">
      <PageHeader title="Tickets (Soporte)" subtitle="Casos de soporte y su estado." />
      <SectionCard>
        <EmptyState
          icon={<IconTicket size={40} />}
          title="En construcción"
          description="Pronto vas a gestionar los casos de soporte de tus clientes desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
