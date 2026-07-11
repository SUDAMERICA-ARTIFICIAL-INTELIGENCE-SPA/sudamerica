"use client";

import { useSucursales } from "@/hooks/useSucursales";
import type { Sucursal } from "@/lib/types";
import { useUiStore } from "@/stores/ui-store";
import { Group, Select, Text } from "@mantine/core";
import { IconMapPin } from "@tabler/icons-react";
import { useMemo } from "react";

export function SucursalSelector() {
  const { data: sucursalesRaw } = useSucursales();
  const { activeSucursalId, setActiveSucursalId } = useUiStore();

  const sucursales: Sucursal[] = useMemo(() => {
    if (!sucursalesRaw) return [];
    if (Array.isArray(sucursalesRaw)) return sucursalesRaw.filter((s) => s.activo);
    const raw = sucursalesRaw as unknown as { data?: Sucursal[] };
    return (raw.data ?? []).filter((s) => s.activo);
  }, [sucursalesRaw]);

  // Don't render if 0 or 1 sucursal
  if (sucursales.length <= 1) return null;

  const options = [
    { value: "__all__", label: "Todas las sucursales" },
    ...sucursales.map((s) => ({
      value: s.id,
      label: s.nombre,
    })),
  ];

  return (
    <Select
      size="xs"
      leftSection={<IconMapPin size={14} />}
      data={options}
      value={activeSucursalId ?? "__all__"}
      onChange={(val) => setActiveSucursalId(val === "__all__" ? null : val)}
      styles={{
        root: { paddingInline: 12, paddingBlock: 8 },
        input: { fontSize: 12 },
      }}
      comboboxProps={{ withinPortal: true }}
      aria-label="Filtrar por sucursal"
    />
  );
}
