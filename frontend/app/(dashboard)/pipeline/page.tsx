"use client";

import { LeadDetail } from "@/components/leads/LeadDetail";
import { LeadForm } from "@/components/leads/LeadForm";
import { KanbanBoard } from "@/components/pipeline/KanbanBoard";
import { PipelineFilters } from "@/components/pipeline/PipelineFilters";
import { PageHeader } from "@/components/ui/PageHeader";
import { useCreateLead, useLeads, useUpdateLead } from "@/hooks/useLeads";
import type { CreateLeadDto, UpdateLeadDto } from "@/hooks/useLeads";
import { useUsuarios } from "@/hooks/useUsuarios";
import type { Lead } from "@/lib/types";
import { Button, Stack } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

export default function PipelinePage() {
  const [search, setSearch] = useState("");
  const [canalFilter, setCanalFilter] = useState("");
  const [asesorFilter, setAsesorFilter] = useState("");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);

  const { data: leadsData, isLoading } = useLeads({ page_size: 100, activo: true } as Parameters<
    typeof useLeads
  >[0]);
  const { data: usuarios } = useUsuarios();
  const { mutate: createLead, isPending: isCreating } = useCreateLead();
  const { mutate: updateLead, isPending: isUpdating } = useUpdateLead();

  const leads = leadsData?.data ?? [];
  const asesores = usuarios ?? [];

  function handleLeadClick(lead: Lead) {
    setSelectedLead(lead);
    setDrawerOpen(true);
  }

  function handleEdit(lead: Lead) {
    setEditingLead(lead);
    setDrawerOpen(false);
    setFormOpen(true);
  }

  function handleFormSubmit(dto: CreateLeadDto | UpdateLeadDto) {
    if (editingLead) {
      updateLead(
        { id: editingLead.id, dto: dto as UpdateLeadDto },
        {
          onSuccess: () => {
            setFormOpen(false);
            setEditingLead(null);
          },
        },
      );
    } else {
      createLead(dto as CreateLeadDto, { onSuccess: () => setFormOpen(false) });
    }
  }

  return (
    <Stack gap="md" h="100%">
      <PageHeader
        title="Pipeline"
        actions={
          <Button
            leftSection={<IconPlus size={16} />}
            color="indigo"
            radius="md"
            aria-label="Nuevo lead"
            onClick={() => {
              setEditingLead(null);
              setFormOpen(true);
            }}
          >
            Nuevo Lead
          </Button>
        }
      />

      <PipelineFilters
        search={search}
        onSearchChange={setSearch}
        canalFilter={canalFilter}
        onCanalChange={setCanalFilter}
        asesorFilter={asesorFilter}
        onAsesorChange={setAsesorFilter}
        asesores={asesores}
      />

      <KanbanBoard
        leads={leads}
        isLoading={isLoading}
        search={search}
        canalFilter={canalFilter}
        asesorFilter={asesorFilter}
        onLeadClick={handleLeadClick}
      />

      <LeadDetail
        lead={selectedLead}
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEdit={handleEdit}
      />

      <LeadForm
        opened={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditingLead(null);
        }}
        onSubmit={handleFormSubmit}
        isLoading={isCreating || isUpdating}
        lead={editingLead}
      />
    </Stack>
  );
}
