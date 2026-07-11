"use client";

import type { LeadsFilters } from "@/hooks/useLeads";
import { LeadCanal, LeadEstado } from "@/lib/enums";
import { ActionIcon, Group, Select, TextInput, Tooltip } from "@mantine/core";
import { IconSearch, IconX } from "@tabler/icons-react";

interface LeadFiltersProps {
  filters: LeadsFilters;
  onFilterChange: (filters: LeadsFilters) => void;
  onReset: () => void;
}

const ESTADO_OPTIONS = [
  { value: LeadEstado.NUEVO, label: "Nuevo" },
  { value: LeadEstado.CONTACTADO, label: "Contactado" },
  { value: LeadEstado.EN_PROCESO, label: "En Proceso" },
  { value: LeadEstado.CONVERTIDO, label: "Convertido" },
  { value: LeadEstado.DESCARTADO, label: "Descartado" },
];

const CANAL_OPTIONS = [
  { value: LeadCanal.WHATSAPP, label: "WhatsApp" },
  { value: LeadCanal.INSTAGRAM, label: "Instagram" },
  { value: LeadCanal.FACEBOOK, label: "Facebook" },
  { value: LeadCanal.WEB, label: "Web" },
  { value: LeadCanal.TELEFONO, label: "Teléfono" },
  { value: LeadCanal.EMAIL, label: "Email" },
  { value: LeadCanal.REFERIDO, label: "Referido" },
];

export function LeadFilters({ filters, onFilterChange, onReset }: LeadFiltersProps) {
  const hasActiveFilters = !!filters.search || !!filters.estado || !!filters.canal;

  return (
    <Group gap="sm" wrap="wrap">
      <TextInput
        placeholder="Buscar por nombre, email..."
        leftSection={<IconSearch size={16} />}
        value={filters.search ?? ""}
        onChange={(e) => onFilterChange({ ...filters, search: e.target.value, page: 1 })}
        aria-label="Buscar clientes"
        style={{ flex: 1, minWidth: 160 }}
        radius="md"
      />
      <Select
        placeholder="Estado"
        data={ESTADO_OPTIONS}
        value={filters.estado ?? null}
        onChange={(v) =>
          onFilterChange({ ...filters, estado: (v as LeadEstado) ?? undefined, page: 1 })
        }
        clearable
        aria-label="Filtrar por estado"
        radius="md"
        style={{ flex: 1, minWidth: 120 }}
      />
      <Select
        placeholder="Canal"
        data={CANAL_OPTIONS}
        value={filters.canal ?? null}
        onChange={(v) =>
          onFilterChange({ ...filters, canal: (v as LeadCanal) ?? undefined, page: 1 })
        }
        clearable
        aria-label="Filtrar por canal"
        radius="md"
        style={{ flex: 1, minWidth: 120 }}
      />
      {hasActiveFilters && (
        <Tooltip label="Limpiar filtros">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="lg"
            aria-label="Limpiar filtros"
            onClick={onReset}
            radius="md"
          >
            <IconX size={16} />
          </ActionIcon>
        </Tooltip>
      )}
    </Group>
  );
}
