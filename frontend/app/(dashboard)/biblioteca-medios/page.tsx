"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionCard } from "@/components/ui/SectionCard";
import { Stack } from "@mantine/core";
import { IconPhoto } from "@tabler/icons-react";

export default function BibliotecaMediosPage() {
  return (
    <Stack gap="lg">
      <PageHeader
        title="Biblioteca de medios"
        subtitle="Fotos, videos y archivos para tus mensajes."
      />
      <SectionCard>
        <EmptyState
          icon={<IconPhoto size={40} />}
          title="En construcción"
          description="Pronto vas a administrar tus fotos y videos desde aquí."
        />
      </SectionCard>
    </Stack>
  );
}
