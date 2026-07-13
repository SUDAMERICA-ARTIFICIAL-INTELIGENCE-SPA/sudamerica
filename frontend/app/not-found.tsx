"use client";

import { ShowroomCatchAllClient } from "@/app/(showroom)/showroom/[rubro]/[[...ruta]]/client";
import { AuthProvider } from "@/lib/auth";
import { activateDemo } from "@/lib/demo/state";
import { Anchor, Center, Loader, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";

/**
 * Página no encontrada = 404.html en el export estático. Cumple doble función:
 *
 *  1. Fallback SPA del showroom. Solo el landing de cada rubro y el árbol del
 *     héroe se pre-renderizan a archivos (ver generateStaticParams del catch-all).
 *     Un hard-load/refresh de una sub de un rubro NO-héroe (p. ej.
 *     `/sudamerica/showroom/restaurante/pipeline`) no tiene archivo → Pages sirve
 *     este 404.html, que lee la URL real y reconstruye la vista en cliente. Así
 *     "todos los rubros navegables" también aguanta deep-links directos.
 *  2. 404 normal para cualquier otra ruta.
 *
 * No hereda el layout de `(showroom)` (los grupos de ruta no envuelven al
 * not-found raíz), así que replica lo mínimo: `activateDemo()` + `AuthProvider`.
 */
export default function NotFound() {
  // Ruta real (sin basePath) resuelta en cliente. `window.location` es fiable en
  // el 404.html servido por Pages; `usePathname` podría reflejar la ruta not-found.
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
    let p = window.location.pathname;
    if (basePath && p.startsWith(basePath)) p = p.slice(basePath.length);
    setPath(p);
  }, []);

  if (path === null) {
    // SSR/primer paint (incl. el HTML estático de 404.html antes de hidratar).
    return (
      <Center mih="100dvh">
        <Loader color="grape" />
      </Center>
    );
  }

  const segs = path.split("/").filter(Boolean);
  if (segs[0] === "showroom" && segs[1]) {
    // Enciende el demo en fase de render, antes de que el efecto de AuthProvider
    // hidrate → isDemoActive() ya es true cuando siembra el tenant sintético.
    activateDemo();
    return (
      <AuthProvider>
        <ShowroomCatchAllClient key={segs[1]} rubro={segs[1]} ruta={segs.slice(2)} />
      </AuthProvider>
    );
  }

  return (
    <Center mih="100dvh" p="xl">
      <Stack align="center" gap="xs">
        <Title order={1}>404</Title>
        <Text c="dimmed">Esta página no existe.</Text>
        <Anchor component={Link} href="/showroom">
          Ir al showroom
        </Anchor>
      </Stack>
    </Center>
  );
}
