import { SHOWROOM_ROUTE_KEYS } from "@/lib/demo/showroom-routes.keys";
import { RUBRO_OPTIONS } from "@/lib/rubros";
import { ShowroomCatchAllClient } from "./client";

// Rubro héroe con snapshots reales (idéntico a `HERO` en lib/demo/resolver.ts):
// su árbol completo de subs se pre-renderiza a HTML. Los demás rubros solo
// pre-renderizan su landing; navegar a sus subs funciona por routing de cliente
// y, en hard-load, cae al fallback SPA de not-found (404.html en Pages).
const HERO = "cosmetica_belleza";

/**
 * Parámetros a materializar en el export estático:
 *  - `{rubro}` (ruta vacía) para los 101 rubros → landing = dashboard/resumen.
 *  - `{HERO, sub}` para las 105 subs del héroe → deep-link directo servible.
 */
export function generateStaticParams() {
  const params: { rubro: string; ruta: string[] }[] = RUBRO_OPTIONS.map((o) => ({
    rubro: o.value,
    ruta: [],
  }));
  for (const key of SHOWROOM_ROUTE_KEYS) {
    params.push({ rubro: HERO, ruta: key.split("/") });
  }
  return params;
}

// dynamicParams se deja en su default (true), que debe ser un literal estático:
//  - export: solo se materializan los params de generateStaticParams; los demás
//    (subs de rubros no-héroe) los sirve 404.html (app/not-found.tsx) en cliente.
//  - standalone: el server rinde on-demand cualquier sub → sin degradar el real.

export default async function ShowroomCatchAllPage({
  params,
}: {
  params: Promise<{ rubro: string; ruta?: string[] }>;
}) {
  const { rubro, ruta } = await params;
  // `key` remonta al cambiar de rubro (QueryClient/cache demo nuevos).
  return <ShowroomCatchAllClient key={rubro} rubro={rubro} ruta={ruta ?? []} />;
}
