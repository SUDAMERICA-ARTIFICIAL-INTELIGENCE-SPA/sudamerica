"use client";

import { ROIInputs, type ROIParams } from "@/components/roi/ROIInputs";
import { ROIReceipt, type ROIReceiptData } from "@/components/roi/ROIReceipt";
import { PageHeader } from "@/components/ui/PageHeader";
import { useDashboardKpis } from "@/hooks/useMetricas";
import { useLatestTenantEconomics } from "@/hooks/useTenantEconomics";
import { efficiencyGain, globalRoi, hoursSaved, timeSavedValue } from "@/lib/kpi-formulas";
import { Grid, Skeleton, Stack } from "@mantine/core";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const ROIBreakdown = dynamic(
  () =>
    import("@/components/roi/ROIBreakdown").then((m) => ({
      default: m.ROIBreakdown,
    })),
  { ssr: false, loading: () => <Skeleton height={280} radius="md" /> },
);

const STORAGE_KEY = "sudamerica_roi_params";

const FALLBACK_PARAMS: ROIParams = {
  hourlyRate: 15,
  saasPrice: 49,
  historicalLrtHours: 4,
  currentLrtHours: 0.5,
  hoursPerConversation: 0.75,
};

function loadSavedParams(): ROIParams {
  if (typeof window === "undefined") return FALLBACK_PARAMS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return FALLBACK_PARAMS;
    const parsed = JSON.parse(raw) as Partial<ROIParams>;
    return { ...FALLBACK_PARAMS, ...parsed };
  } catch {
    return FALLBACK_PARAMS;
  }
}

export default function ROIPage() {
  const [params, setParams] = useState<ROIParams>(loadSavedParams);
  const { data: kpis } = useDashboardKpis();
  const { data: economics } = useLatestTenantEconomics();
  const seededFromApi = useRef(false);

  const handleChange = useCallback((next: ROIParams) => {
    setParams(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* quota exceeded — ignore */
    }
  }, []);

  useEffect(() => {
    if (seededFromApi.current) return;

    const patches: Partial<ROIParams> = {};

    const lrtMs = kpis?.avg_lead_response_time_ms;
    if (lrtMs != null) {
      patches.currentLrtHours = Number((lrtMs / 3_600_000).toFixed(2));
    }

    if (economics) {
      const totalConv = economics.leads_convertidos || 0;
      const hoursTotal = economics.horas_ahorradas || 0;
      if (totalConv > 0 && hoursTotal > 0) {
        patches.hoursPerConversation = Number((hoursTotal / totalConv).toFixed(2));
      }
    }

    if (Object.keys(patches).length > 0) {
      seededFromApi.current = true;
      setParams((prev) => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return prev;
        return { ...prev, ...patches };
      });
    }
  }, [kpis, economics]);

  const receipt = useMemo<ROIReceiptData>(() => {
    const iaResolved = kpis?.ia_auto_resueltas ?? 0;
    const ahorroIa = kpis?.ahorro_ia_usd ?? 0;

    const savedHours = hoursSaved(iaResolved, params.hoursPerConversation);
    const timeSaved = timeSavedValue(iaResolved, params.hourlyRate, params.hoursPerConversation);
    const incRevenue = ahorroIa;
    const totalBenefit = timeSaved + incRevenue;
    const netRoi = totalBenefit - params.saasPrice;
    const roiPct = globalRoi(incRevenue, timeSaved, params.saasPrice);

    const efficiency = efficiencyGain(
      params.historicalLrtHours * 3_600_000,
      params.currentLrtHours * 3_600_000,
    );

    return {
      timeSavedUsd: timeSaved,
      incrementalRevenue: incRevenue,
      totalBenefit,
      saasPrice: params.saasPrice,
      netRoi,
      roiPercent: roiPct,
      hoursSaved: savedHours,
      efficiencyGain: efficiency,
    };
  }, [kpis, params]);

  return (
    <Stack gap="lg">
      <PageHeader title="Calculadora ROI" />

      <ROIInputs params={params} onChange={handleChange} />

      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 5 }}>
          <ROIReceipt data={receipt} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <ROIBreakdown
            timeSavedUsd={receipt.timeSavedUsd}
            incrementalRevenue={receipt.incrementalRevenue}
            saasPrice={receipt.saasPrice}
          />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
