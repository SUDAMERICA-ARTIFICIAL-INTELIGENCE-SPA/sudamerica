"use client";

import { MesasManager } from "@/components/configuracion/MesasManager";
import { PageHeader } from "@/components/ui/PageHeader";
import { useRubroLabels } from "@/hooks/useRubroLabels";
import { RUBRO_DEFAULT, plural } from "@/lib/rubros";
import { Stack } from "@mantine/core";

export default function MesasPage() {
  const rubro = useRubroLabels();
  const titulo =
    rubro.key === RUBRO_DEFAULT ? "Mesas del Restaurante" : plural(rubro.labels.recurso);

  return (
    <Stack gap="lg">
      <PageHeader title={titulo} />
      <MesasManager />
    </Stack>
  );
}
