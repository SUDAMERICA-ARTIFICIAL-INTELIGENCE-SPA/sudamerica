import { describe, expect, it } from "vitest";
import { OnboardingStep, type TenantOnboardingState, resolveOnboardingStep } from "./onboarding";

const ISO = "2026-07-16T12:00:00.000Z";

describe("resolveOnboardingStep — reanudación del wizard", () => {
  it("sin autenticar siempre arranca en Cuenta (paso 0)", () => {
    expect(resolveOnboardingStep({}, false)).toBe(OnboardingStep.Cuenta);
    // aunque el estado tuviera timestamps, sin auth no se puede avanzar
    const full: TenantOnboardingState = {
      rubro_completed_at: ISO,
      perfil_completed_at: ISO,
      capacidades_reviewed_at: ISO,
    };
    expect(resolveOnboardingStep(full, false)).toBe(OnboardingStep.Cuenta);
  });

  it("autenticado sin progreso arranca en Rubro (paso 1)", () => {
    expect(resolveOnboardingStep({}, true)).toBe(OnboardingStep.Rubro);
  });

  it("avanza a Perfil cuando el rubro está resuelto", () => {
    expect(resolveOnboardingStep({ rubro_completed_at: ISO }, true)).toBe(OnboardingStep.Perfil);
  });

  it("avanza a Modulos cuando perfil está resuelto", () => {
    expect(resolveOnboardingStep({ rubro_completed_at: ISO, perfil_completed_at: ISO }, true)).toBe(
      OnboardingStep.Modulos,
    );
  });

  it("avanza a Datos tras revisar módulos", () => {
    expect(
      resolveOnboardingStep(
        { rubro_completed_at: ISO, perfil_completed_at: ISO, capacidades_reviewed_at: ISO },
        true,
      ),
    ).toBe(OnboardingStep.Datos);
  });

  it("los pasos opcionales cuentan como resueltos al saltarse", () => {
    const base: TenantOnboardingState = {
      rubro_completed_at: ISO,
      perfil_completed_at: ISO,
      capacidades_reviewed_at: ISO,
    };
    // Datos saltado → salta a WhatsApp
    expect(resolveOnboardingStep({ ...base, datos_skipped_at: ISO }, true)).toBe(
      OnboardingStep.WhatsApp,
    );
    // Datos completado → también a WhatsApp
    expect(resolveOnboardingStep({ ...base, datos_completed_at: ISO }, true)).toBe(
      OnboardingStep.WhatsApp,
    );
  });

  it("llega a Listo cuando todos los pasos (incluidos opcionales) están resueltos", () => {
    const done: TenantOnboardingState = {
      rubro_completed_at: ISO,
      perfil_completed_at: ISO,
      capacidades_reviewed_at: ISO,
      datos_skipped_at: ISO,
      whatsapp_completed_at: ISO,
    };
    expect(resolveOnboardingStep(done, true)).toBe(OnboardingStep.Listo);
  });
});
