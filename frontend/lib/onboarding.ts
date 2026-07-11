import { TenantPlan } from "@/lib/enums";
import type { Tenant } from "@/lib/types";

export interface TenantOnboardingState {
  required?: boolean;
  started_at?: string;
  business_completed_at?: string;
  menu_completed_at?: string;
  menu_skipped_at?: string;
  ai_completed_at?: string;
  ai_skipped_at?: string;
  whatsapp_completed_at?: string;
  whatsapp_skipped_at?: string;
  completed_at?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function getTenantConfig(tenant: Tenant | null | undefined): Record<string, unknown> {
  return asRecord(tenant?.config) ?? {};
}

export function getTenantOnboardingState(tenant: Tenant | null | undefined): TenantOnboardingState {
  const config = getTenantConfig(tenant);
  return (asRecord(config.onboarding) as TenantOnboardingState | null) ?? {};
}

export function needsTenantOnboarding(tenant: Tenant | null | undefined): boolean {
  const onboarding = getTenantOnboardingState(tenant);
  return Boolean(onboarding.required && !onboarding.completed_at);
}

export function normalizeTenantPlan(plan: string | null | undefined): TenantPlan {
  if (!plan || plan === TenantPlan.FREE) {
    return TenantPlan.ESTANDAR;
  }
  if (Object.values(TenantPlan).includes(plan as TenantPlan)) {
    return plan as TenantPlan;
  }
  return TenantPlan.ESTANDAR;
}
