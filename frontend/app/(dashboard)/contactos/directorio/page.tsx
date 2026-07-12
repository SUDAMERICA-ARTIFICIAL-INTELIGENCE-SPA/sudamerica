"use client";

import { ClienteCard } from "@/components/clientes/ClienteCard";
import { ClienteFilters } from "@/components/clientes/ClienteFilters";
import { LeadDetail } from "@/components/leads/LeadDetail";
import { LeadFilters } from "@/components/leads/LeadFilters";
import { LeadForm } from "@/components/leads/LeadForm";
import { LeadsTable } from "@/components/leads/LeadsTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useCreateLead, useLeads, useUpdateLead } from "@/hooks/useLeads";
import type { CreateLeadDto, LeadsFilters, UpdateLeadDto } from "@/hooks/useLeads";
import type { Lead } from "@/lib/types";
import { Button, SegmentedControl, SimpleGrid, Skeleton, Stack } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

const DEFAULT_FILTERS: LeadsFilters = { page: 1, page_size: 20 };

type ViewMode = "crm" | "clientes";

function ClienteGridSkeleton() {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} height={200} radius={12} />
      ))}
    </SimpleGrid>
  );
}

export default function LeadsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("crm");
  const [filters, setFilters] = useState<LeadsFilters>(DEFAULT_FILTERS);
  const [clienteEstadoFilter, setClienteEstadoFilter] = useState<string | null>(null);
  const [formOpened, setFormOpened] = useState(false);
  const [detailOpened, setDetailOpened] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);

  // Build filters for clientes view
  const clienteFilters: LeadsFilters = {
    ...DEFAULT_FILTERS,
    ...(clienteEstadoFilter ? { estado_cliente: clienteEstadoFilter } : {}),
    order_by: "total_gastado",
  };

  const { data: clienteData, isLoading: isClienteLoading } = useLeads(
    viewMode === "clientes" ? clienteFilters : undefined,
  );

  const { mutate: createLead, isPending: isCreating } = useCreateLead();
  const { mutate: updateLead, isPending: isUpdating } = useUpdateLead();

  function handleViewLead(lead: Lead) {
    setSelectedLead(lead);
    setDetailOpened(true);
  }

  function handleEditLead(lead: Lead) {
    setEditingLead(lead);
    setDetailOpened(false);
    setFormOpened(true);
  }

  function handleOpenCreate() {
    setEditingLead(null);
    setFormOpened(true);
  }

  function handleFormClose() {
    setFormOpened(false);
    setEditingLead(null);
  }

  function handleFormSubmit(dto: CreateLeadDto | UpdateLeadDto) {
    if (editingLead) {
      updateLead(
        { id: editingLead.id, dto: dto as UpdateLeadDto },
        { onSuccess: () => setFormOpened(false) },
      );
    } else {
      createLead(dto as CreateLeadDto, { onSuccess: () => setFormOpened(false) });
    }
  }

  const clienteLeads = clienteData?.data ?? [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Clientes"
        actions={
          <>
            <SegmentedControl
              value={viewMode}
              onChange={(v) => setViewMode(v as ViewMode)}
              data={[
                { value: "crm", label: "Vista CRM" },
                { value: "clientes", label: "Vista Clientes" },
              ]}
              radius="md"
              aria-label="Cambiar vista de leads"
            />
            <Button
              leftSection={<IconPlus size={16} />}
              color="indigo"
              onClick={handleOpenCreate}
              aria-label="Crear nuevo cliente"
              radius="md"
            >
              Nuevo Cliente
            </Button>
          </>
        }
      />

      {viewMode === "crm" ? (
        <>
          {/* CRM View: Filters + Table */}
          <LeadFilters
            filters={filters}
            onFilterChange={setFilters}
            onReset={() => setFilters(DEFAULT_FILTERS)}
          />
          <LeadsTable
            filters={filters}
            onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
            onViewLead={handleViewLead}
            onEditLead={handleEditLead}
          />
        </>
      ) : (
        <>
          {/* Clientes View: ClienteFilters + Card Grid */}
          <ClienteFilters value={clienteEstadoFilter} onChange={setClienteEstadoFilter} />
          {isClienteLoading ? (
            <ClienteGridSkeleton />
          ) : clienteLeads.length === 0 ? (
            <EmptyState
              title={`No hay clientes${clienteEstadoFilter ? ` con estado ${clienteEstadoFilter}` : ""}`}
            />
          ) : (
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
              {clienteLeads.map((lead) => (
                <ClienteCard key={lead.id} lead={lead} onClick={handleViewLead} />
              ))}
            </SimpleGrid>
          )}
        </>
      )}

      {/* Detail drawer */}
      <LeadDetail
        lead={selectedLead}
        opened={detailOpened}
        onClose={() => setDetailOpened(false)}
        onEdit={handleEditLead}
      />

      {/* Create/Edit modal */}
      <LeadForm
        opened={formOpened}
        onClose={handleFormClose}
        onSubmit={handleFormSubmit}
        isLoading={isCreating || isUpdating}
        lead={editingLead}
      />
    </Stack>
  );
}
