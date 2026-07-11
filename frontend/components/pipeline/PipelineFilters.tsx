"use client";

import { LeadCanal } from "@/lib/enums";
import type { Usuario } from "@/lib/types";
import { Group, Select, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";

const CANAL_OPTIONS = [
  { value: "", label: "Todos los canales" },
  ...Object.values(LeadCanal).map((c) => ({ value: c, label: c })),
];

interface PipelineFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  canalFilter: string;
  onCanalChange: (v: string) => void;
  asesorFilter: string;
  onAsesorChange: (v: string) => void;
  asesores: Usuario[];
}

export function PipelineFilters({
  search,
  onSearchChange,
  canalFilter,
  onCanalChange,
  asesorFilter,
  onAsesorChange,
  asesores,
}: PipelineFiltersProps) {
  const asesorOptions = [
    { value: "", label: "Todos los asesores" },
    ...asesores.map((u) => ({ value: u.id, label: u.nombre })),
  ];

  return (
    <Group gap="sm" wrap="wrap" aria-label="Filtros del pipeline">
      <TextInput
        placeholder="Buscar lead..."
        value={search}
        onChange={(e) => onSearchChange(e.currentTarget.value)}
        leftSection={<IconSearch size={16} />}
        radius="md"
        size="sm"
        style={{ minWidth: 200 }}
        aria-label="Buscar lead por nombre"
      />
      <Select
        data={CANAL_OPTIONS}
        value={canalFilter}
        onChange={(v) => onCanalChange(v ?? "")}
        radius="md"
        size="sm"
        style={{ minWidth: 160 }}
        aria-label="Filtrar por canal"
        allowDeselect={false}
      />
      <Select
        data={asesorOptions}
        value={asesorFilter}
        onChange={(v) => onAsesorChange(v ?? "")}
        radius="md"
        size="sm"
        style={{ minWidth: 180 }}
        aria-label="Filtrar por asesor"
        allowDeselect={false}
      />
    </Group>
  );
}
