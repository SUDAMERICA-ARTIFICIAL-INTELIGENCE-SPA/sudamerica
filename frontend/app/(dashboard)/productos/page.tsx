import { redirect } from "next/navigation";

/**
 * Ruta huérfana DEPRECADA (decisión Fase 0 del cableado P2): duplicaba /carta
 * (mismo catálogo, otra tabla). Redirect permanente — los deep-links viejos siguen
 * funcionando. Los componentes de components/productos/ quedan para reuso desde /carta.
 */
export default function ProductosPage() {
  redirect("/carta");
}
