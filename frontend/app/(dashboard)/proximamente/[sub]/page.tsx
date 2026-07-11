"use client";

import { Proximamente } from "@/components/ui/Proximamente";
import { NAV_TREE_P2 } from "@/lib/nav-tree";
import { useParams } from "next/navigation";

/**
 * Destino de toda sub P2 sin ruta construida (NAV_TREE_ROUTES = null): ruta real
 * /proximamente/<sub>, así el NavLink/breadcrumb/active-state del shell funcionan
 * sin tocar el render. Sub desconocida ⇒ placeholder genérico (nunca pantalla rota).
 */
export default function ProximamentePage() {
  const params = useParams<{ sub: string }>();
  const subId = params.sub;

  for (const categoria of NAV_TREE_P2) {
    const sub = categoria.subs.find((s) => s.id === subId);
    if (sub) {
      return <Proximamente label={sub.label} categoria={categoria.label} vistas={sub.vistas} />;
    }
  }
  return <Proximamente label="Esta sección" />;
}
