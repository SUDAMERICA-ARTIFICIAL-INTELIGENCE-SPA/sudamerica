import {
  aiRoi,
  autoResolutionRate,
  averageLeadResponseTime,
  costPerConversation,
  customerAcquisitionCost,
  efficiencyGain,
  forecastAccuracy,
  globalRoi,
  hoursSaved,
  lifetimeValue,
  ltvCacRatio,
  netPromoterScore,
  pipelineCoverage,
  pipelineVelocity,
  timeSavedValue,
  winRate,
  workloadPerAdvisor,
} from "@/lib/kpi-formulas";
import { describe, expect, it } from "vitest";

describe("Pipeline KPIs", () => {
  it("pipelineVelocity returns correct value", () => {
    // (10 * 5000 * 0.3) / 30 = 500
    expect(pipelineVelocity(10, 5000, 0.3, 30)).toBeCloseTo(500);
  });

  it("pipelineVelocity returns 0 when avgCycleDays is 0", () => {
    expect(pipelineVelocity(10, 5000, 0.3, 0)).toBe(0);
  });

  it("winRate calculates correctly", () => {
    expect(winRate(30, 70)).toBe(30);
  });

  it("winRate returns 0 when no deals", () => {
    expect(winRate(0, 0)).toBe(0);
  });

  it("pipelineCoverage returns 0 when quota is 0", () => {
    expect(pipelineCoverage(100000, 0)).toBe(0);
  });

  it("forecastAccuracy returns 100 when actual equals forecast", () => {
    expect(forecastAccuracy(1000, 1000)).toBe(100);
  });
});

describe("AI Efficiency KPIs", () => {
  it("autoResolutionRate returns correct percentage", () => {
    expect(autoResolutionRate(80, 100)).toBe(80);
  });

  it("autoResolutionRate returns 0 when totalAi is 0", () => {
    expect(autoResolutionRate(10, 0)).toBe(0);
  });

  it("costPerConversation divides correctly", () => {
    expect(costPerConversation(50, 100)).toBe(0.5);
  });

  it("hoursSaved uses 0.75h default", () => {
    expect(hoursSaved(100)).toBe(75);
  });

  it("aiRoi returns 0 when cost is 0", () => {
    expect(aiRoi(1000, 0)).toBe(0);
  });

  it("aiRoi calculates correctly", () => {
    expect(aiRoi(2000, 1000)).toBe(100);
  });
});

describe("Client & Retention KPIs", () => {
  it("CAC divides correctly", () => {
    expect(customerAcquisitionCost(5000, 100)).toBe(50);
  });

  it("LTV returns 0 when churnRate is 0", () => {
    expect(lifetimeValue(100, 0.5, 0)).toBe(0);
  });

  it("LTV:CAC ratio is correct", () => {
    expect(ltvCacRatio(3000, 1000)).toBe(3);
  });

  it("NPS calculates correctly", () => {
    expect(netPromoterScore(60, 10, 100)).toBe(50);
  });
});

describe("Operational KPIs", () => {
  it("averageLeadResponseTime returns 0 when no leads", () => {
    expect(averageLeadResponseTime(1000, 0)).toBe(0);
  });

  it("workloadPerAdvisor returns 0 when no advisors", () => {
    expect(workloadPerAdvisor(100, 0)).toBe(0);
  });

  it("workloadPerAdvisor distributes evenly", () => {
    expect(workloadPerAdvisor(100, 5)).toBe(20);
  });
});

describe("ROI Calculator", () => {
  it("timeSavedValue calculates correctly", () => {
    expect(timeSavedValue(100, 20)).toBe(1500); // 100 * 0.75 * 20
  });

  it("efficiencyGain returns 0 when historical is 0", () => {
    expect(efficiencyGain(0, 5000)).toBe(0);
  });

  it("efficiencyGain calculates improvement", () => {
    expect(efficiencyGain(10000, 5000)).toBe(50);
  });

  it("globalRoi returns 0 when saasPrice is 0", () => {
    expect(globalRoi(5000, 1000, 0)).toBe(0);
  });

  it("globalRoi calculates positive ROI", () => {
    expect(globalRoi(5000, 1000, 2000)).toBe(200); // (5000+1000-2000)/2000 * 100
  });
});
