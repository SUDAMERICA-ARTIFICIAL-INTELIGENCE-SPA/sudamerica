import { TenantPlan } from "@/lib/enums";
import type { Tenant } from "@/lib/types";

export interface TenantOnboardingState {
  required?: boolean;
  started_at?: string;
  /** Wizard canónico (7 pasos). Cada timestamp marca un paso resuelto. */
  cuenta_completed_at?: string;
  rubro_completed_at?: string;
  perfil_completed_at?: string;
  capacidades_reviewed_at?: string;
  datos_completed_at?: string;
  datos_skipped_at?: string;
  // Claves legadas del wizard anterior (Negocio/Carta/IA) — se conservan por
  // compatibilidad con tenants ya migrados; el flujo nuevo no las escribe.
  business_completed_at?: string;
  menu_completed_at?: string;
  menu_skipped_at?: string;
  ai_completed_at?: string;
  ai_skipped_at?: string;
  whatsapp_completed_at?: string;
  whatsapp_skipped_at?: string;
  completed_at?: string;
}

/** Pasos del wizard de onboarding, en orden. El índice es el paso activo del Stepper. */
export enum OnboardingStep {
  Cuenta = 0,
  Rubro = 1,
  Perfil = 2,
  Modulos = 3,
  Datos = 4,
  WhatsApp = 5,
  Listo = 6,
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

/**
 * Resuelve el paso activo del wizard a partir del estado persistido y de si el usuario
 * ya está autenticado. Es la única fuente de verdad para reanudar el onboarding: cerrar
 * y reabrir el navegador retoma el primer paso no resuelto.
 *
 * - Sin autenticar → siempre `Cuenta` (paso 0, pre-auth).
 * - Autenticado → primer paso cuyo timestamp aún no existe. Los pasos opcionales (Datos,
 *   WhatsApp) se consideran resueltos tanto al completarse como al saltarse.
 */
export function resolveOnboardingStep(
  onboarding: TenantOnboardingState,
  isAuthenticated: boolean,
): OnboardingStep {
  if (!isAuthenticated) return OnboardingStep.Cuenta;
  if (!onboarding.rubro_completed_at) return OnboardingStep.Rubro;
  if (!onboarding.perfil_completed_at) return OnboardingStep.Perfil;
  if (!onboarding.capacidades_reviewed_at) return OnboardingStep.Modulos;
  if (!onboarding.datos_completed_at && !onboarding.datos_skipped_at) return OnboardingStep.Datos;
  if (!onboarding.whatsapp_completed_at && !onboarding.whatsapp_skipped_at) {
    return OnboardingStep.WhatsApp;
  }
  return OnboardingStep.Listo;
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
