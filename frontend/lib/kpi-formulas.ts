// Pure KPI formula functions — all unit-testable, no side effects

// ─── Pipeline KPIs ────────────────────────────────────────────────────────────

export function pipelineVelocity(
  opportunities: number,
  avgDealValue: number,
  winRate: number,
  avgCycleDays: number,
): number {
  if (avgCycleDays === 0) return 0;
  return (opportunities * avgDealValue * winRate) / avgCycleDays;
}

export function winRate(won: number, lost: number): number {
  const total = won + lost;
  if (total === 0) return 0;
  return (won / total) * 100;
}

export function pipelineCoverage(openPipeline: number, quota: number): number {
  if (quota === 0) return 0;
  return openPipeline / quota;
}

export function forecastAccuracy(actual: number, forecast: number): number {
  if (forecast === 0) return 0;
  return (actual / forecast) * 100;
}

// ─── AI Efficiency KPIs ───────────────────────────────────────────────────────

export function autoResolutionRate(aiResolvedNoHuman: number, totalAi: number): number {
  if (totalAi === 0) return 0;
  return (aiResolvedNoHuman / totalAi) * 100;
}

export function costPerConversation(totalTokenCost: number, totalConversations: number): number {
  if (totalConversations === 0) return 0;
  return totalTokenCost / totalConversations;
}

export function hoursSaved(aiResolved: number, hoursPerConversation = 0.75): number {
  return aiResolved * hoursPerConversation;
}

export function aiRoi(revenueFromAiLeads: number, aiCost: number): number {
  if (aiCost === 0) return 0;
  return ((revenueFromAiLeads - aiCost) / aiCost) * 100;
}

// ─── Client & Retention KPIs ─────────────────────────────────────────────────

export function customerAcquisitionCost(marketingSpend: number, newCustomers: number): number {
  if (newCustomers === 0) return 0;
  return marketingSpend / newCustomers;
}

export function lifetimeValue(arpu: number, marginRate: number, churnRate: number): number {
  if (churnRate === 0) return 0;
  return (arpu * marginRate) / churnRate;
}

export function ltvCacRatio(ltv: number, cac: number): number {
  if (cac === 0) return 0;
  return ltv / cac;
}

export function netPromoterScore(promoters: number, detractors: number, total: number): number {
  if (total === 0) return 0;
  return (promoters / total - detractors / total) * 100;
}

// ─── Operational KPIs ────────────────────────────────────────────────────────

export function averageLeadResponseTime(totalResponseMs: number, leadCount: number): number {
  if (leadCount === 0) return 0;
  return totalResponseMs / leadCount;
}

export function workloadPerAdvisor(activeLeads: number, advisorCount: number): number {
  if (advisorCount === 0) return 0;
  return activeLeads / advisorCount;
}

// ─── ROI Calculator ───────────────────────────────────────────────────────────

export function timeSavedValue(
  aiResolved: number,
  hourlyRate: number,
  hoursPerConversation = 0.75,
): number {
  return aiResolved * hoursPerConversation * hourlyRate;
}

export function efficiencyGain(lrtHistoricalMs: number, lrtCurrentMs: number): number {
  if (lrtHistoricalMs === 0) return 0;
  return ((lrtHistoricalMs - lrtCurrentMs) / lrtHistoricalMs) * 100;
}

export function globalRoi(
  revenueIncremental: number,
  costSavings: number,
  saasPrice: number,
): number {
  if (saasPrice === 0) return 0;
  return ((revenueIncremental + costSavings - saasPrice) / saasPrice) * 100;
}
