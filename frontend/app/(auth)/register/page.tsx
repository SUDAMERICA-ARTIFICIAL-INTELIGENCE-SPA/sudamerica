import { redirect } from "next/navigation";

/**
 * El registro ES el onboarding (wizard continuo): su primer paso crea la cuenta. Esta ruta
 * existe solo por compatibilidad con enlaces históricos a /register — redirige al wizard.
 */
export default function RegisterPage() {
  redirect("/registro");
}
