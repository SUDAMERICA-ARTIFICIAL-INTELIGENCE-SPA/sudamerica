"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { NumberInput, SimpleGrid } from "@mantine/core";

export interface ROIParams {
  hourlyRate: number;
  saasPrice: number;
  historicalLrtHours: number;
  currentLrtHours: number;
  hoursPerConversation: number;
}

interface ROIInputsProps {
  params: ROIParams;
  onChange: (params: ROIParams) => void;
}

export function ROIInputs({ params, onChange }: ROIInputsProps) {
  function update(field: keyof ROIParams, value: number) {
    onChange({ ...params, [field]: value });
  }

  return (
    <SectionCard title="Parámetros del cálculo">
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        <NumberInput
          label="Valor/hora asesor (USD)"
          description="Costo promedio por hora de trabajo humano"
          placeholder="15"
          min={1}
          max={500}
          prefix="$"
          value={params.hourlyRate}
          onChange={(v) => update("hourlyRate", Number(v) || 0)}
          radius="md"
          aria-label="Valor por hora del asesor en USD"
        />
        <NumberInput
          label="Precio SaaS / mes (USD)"
          description="Tu suscripción mensual a Sudamérica AI"
          placeholder="49"
          min={0}
          max={9999}
          prefix="$"
          value={params.saasPrice}
          onChange={(v) => update("saasPrice", Number(v) || 0)}
          radius="md"
          aria-label="Precio del SaaS por mes en USD"
        />
        <NumberInput
          label="Duración promedio conversación (h)"
          description="Tiempo promedio que toma una conversación manual"
          placeholder="0.75"
          min={0.1}
          max={8}
          step={0.05}
          decimalScale={2}
          suffix="h"
          value={params.hoursPerConversation}
          onChange={(v) => update("hoursPerConversation", Number(v) || 0.75)}
          radius="md"
          aria-label="Duración promedio de conversación en horas"
        />
        <NumberInput
          label="Tiempo resp. histórico (h)"
          description="Horas promedio de respuesta antes de Sudamérica AI"
          placeholder="4"
          min={0}
          max={72}
          suffix="h"
          value={params.historicalLrtHours}
          onChange={(v) => update("historicalLrtHours", Number(v) || 0)}
          radius="md"
          aria-label="Tiempo de respuesta histórico en horas"
        />
        <NumberInput
          label="Tiempo resp. actual (h)"
          description="Horas promedio de respuesta actual con Sudamérica AI"
          placeholder="0.5"
          min={0}
          max={72}
          step={0.1}
          decimalScale={2}
          suffix="h"
          value={params.currentLrtHours}
          onChange={(v) => update("currentLrtHours", Number(v) || 0)}
          radius="md"
          aria-label="Tiempo de respuesta actual en horas"
        />
      </SimpleGrid>
    </SectionCard>
  );
}
