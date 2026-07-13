"use client";

import { ShowroomShell } from "@/components/showroom/ShowroomShell";
import { ShowroomNavProvider } from "@/lib/demo/showroom-nav";
import {
  SHOWROOM_DEFAULT_ROUTE,
  SHOWROOM_ROUTES,
} from "@/lib/demo/showroom-routes.generated";
import { setDemoRubro } from "@/lib/demo/state";
import { type RubroDef, getRubroDef, resolveRubro } from "@/lib/rubros";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentType } from "react";
import { useState } from "react";

function makeDemoClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: Number.POSITIVE_INFINITY },
    },
  });
}

/** Página de (dashboard) para la `ruta`, o el dashboard/resumen por defecto. */
function pageFor(rutaKey: string): ComponentType {
  const Page = SHOWROOM_ROUTES[rutaKey] ?? SHOWROOM_ROUTES[SHOWROOM_DEFAULT_ROUTE];
  // SHOWROOM_DEFAULT_ROUTE ("dashboard") siempre existe en el registro generado.
  return Page as ComponentType;
}

function ShowroomRubro({
  def,
  base,
  rutaKey,
}: {
  def: RubroDef;
  base: string;
  rutaKey: string;
}) {
  // Fija el rubro activo antes de que los hooks disparen sus queries; el resolver
  // lo lee al ejecutar la queryFn (post-commit). Determinista e idempotente.
  setDemoRubro(def.key);
  const [queryClient] = useState(makeDemoClient);
  const Page = pageFor(rutaKey);

  return (
    <QueryClientProvider client={queryClient}>
      <ShowroomNavProvider base={base}>
        <ShowroomShell>
          <Page />
        </ShowroomShell>
      </ShowroomNavProvider>
    </QueryClientProvider>
  );
}

/**
 * Cliente del catch-all del showroom. Recibe `rubro`/`ruta` por props (los
 * resuelve el server component contenedor o el fallback de not-found), monta el
 * shell REAL del dashboard en modo demo y renderiza la página real de
 * (dashboard) correspondiente, con datos vía la capa demo (snapshots del rubro
 * héroe / reskin para el resto).
 *
 * `key={def.key}` (aplicado por quien lo monta) remonta al cambiar de rubro →
 * QueryClient nuevo (cache limpio) y `setDemoRubro` re-ejecutado. Navegar entre
 * subs del MISMO rubro no remonta → la cache demo persiste (nav instantánea).
 */
export function ShowroomCatchAllClient({
  rubro,
  ruta,
}: {
  rubro: string;
  ruta: string[];
}) {
  const def = getRubroDef(resolveRubro({ rubro }));
  const base = `/showroom/${rubro}`;
  const rutaKey = ruta.join("/") || SHOWROOM_DEFAULT_ROUTE;
  return <ShowroomRubro def={def} base={base} rutaKey={rutaKey} />;
}
