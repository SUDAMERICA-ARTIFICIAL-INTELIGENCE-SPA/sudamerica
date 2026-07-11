"use client";

import { KanbanColumn } from "@/components/pipeline/KanbanColumn";
import { type LeadCanal, LeadEstado } from "@/lib/enums";
import type { Lead } from "@/lib/types";
import { ScrollArea } from "@mantine/core";
import { useMemo } from "react";

const KANBAN_COLUMNS: LeadEstado[] = [
  LeadEstado.NUEVO,
  LeadEstado.CONTACTADO,
  LeadEstado.EN_PROCESO,
  LeadEstado.CONVERTIDO,
  LeadEstado.DESCARTADO,
];

interface KanbanBoardProps {
  leads: Lead[];
  isLoading: boolean;
  search: string;
  canalFilter: string;
  asesorFilter: string;
  onLeadClick: (lead: Lead) => void;
}

export function KanbanBoard({
  leads,
  isLoading,
  search,
  canalFilter,
  asesorFilter,
  onLeadClick,
}: KanbanBoardProps) {
  const filtered = useMemo(() => {
    return leads.filter((lead) => {
      const matchSearch = !search || lead.nombre.toLowerCase().includes(search.toLowerCase());
      const matchCanal = !canalFilter || lead.canal === (canalFilter as LeadCanal);
      const matchAsesor = !asesorFilter || lead.asesor_id === asesorFilter;
      return matchSearch && matchCanal && matchAsesor;
    });
  }, [leads, search, canalFilter, asesorFilter]);

  const byEstado = useMemo(() => {
    const map: Record<LeadEstado, Lead[]> = {
      [LeadEstado.NUEVO]: [],
      [LeadEstado.CONTACTADO]: [],
      [LeadEstado.EN_PROCESO]: [],
      [LeadEstado.CONVERTIDO]: [],
      [LeadEstado.DESCARTADO]: [],
    };
    for (const lead of filtered) {
      map[lead.estado].push(lead);
    }
    return map;
  }, [filtered]);

  return (
    <ScrollArea type="auto" scrollbarSize={6} aria-label="Kanban board del pipeline">
      <div
        style={{
          display: "flex",
          gap: "16px",
          alignItems: "flex-start",
          paddingBottom: "16px",
          minWidth: "fit-content",
        }}
      >
        {KANBAN_COLUMNS.map((estado) => (
          <KanbanColumn
            key={estado}
            estado={estado}
            leads={byEstado[estado]}
            isLoading={isLoading}
            onLeadClick={onLeadClick}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
