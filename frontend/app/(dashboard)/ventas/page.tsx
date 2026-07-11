"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { VentaForm } from "@/components/ventas/VentaForm";
import { VentasTable } from "@/components/ventas/VentasTable";
import { useCreateVenta } from "@/hooks/useVentas";
import type { CreateVentaDto, VentasFilters } from "@/hooks/useVentas";
import { Button, Stack } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

export default function VentasPage() {
  const [formOpened, setFormOpened] = useState(false);
  const [page, setPage] = useState(1);
  const { mutate: createVenta, isPending: isCreating } = useCreateVenta();

  const filters: VentasFilters = { page, page_size: 20 };

  function handleSubmit(dto: CreateVentaDto) {
    createVenta(dto, { onSuccess: () => setFormOpened(false) });
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="Ventas"
        actions={
          <Button
            leftSection={<IconPlus size={16} />}
            color="indigo"
            onClick={() => setFormOpened(true)}
            aria-label="Registrar nueva venta"
            radius="md"
          >
            Registrar Venta
          </Button>
        }
      />

      <VentasTable filters={filters} onPageChange={setPage} />

      <VentaForm
        opened={formOpened}
        onClose={() => setFormOpened(false)}
        onSubmit={handleSubmit}
        isLoading={isCreating}
      />
    </Stack>
  );
}
