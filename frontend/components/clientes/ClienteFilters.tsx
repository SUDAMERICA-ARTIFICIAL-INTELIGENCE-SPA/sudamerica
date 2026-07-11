"use client";

import { ClienteEstado, CLIENTE_ESTADO_LABELS } from "@/lib/enums";
import { SegmentedControl } from "@mantine/core";

interface ClienteFiltersProps {
  value: string | null;
  onChange: (v: string | null) => void;
}

const SEGMENTED_DATA = [
  { value: "__ALL__", label: "Todos" },
  { value: ClienteEstado.VIP, label: CLIENTE_ESTADO_LABELS[ClienteEstado.VIP] },
  { value: ClienteEstado.FRECUENTE, label: CLIENTE_ESTADO_LABELS[ClienteEstado.FRECUENTE] },
  { value: ClienteEstado.OCASIONAL, label: CLIENTE_ESTADO_LABELS[ClienteEstado.OCASIONAL] },
  { value: ClienteEstado.INACTIVO, label: CLIENTE_ESTADO_LABELS[ClienteEstado.INACTIVO] },
];

export function ClienteFilters({ value, onChange }: ClienteFiltersProps) {
  return (
    <SegmentedControl
      value={value ?? "__ALL__"}
      onChange={(v) => onChange(v === "__ALL__" ? null : v)}
      data={SEGMENTED_DATA}
      radius="md"
      aria-label="Filtrar clientes por estado"
    />
  );
}
