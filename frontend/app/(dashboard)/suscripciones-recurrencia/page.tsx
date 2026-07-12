import { redirect } from "next/navigation";

/**
 * Ruta plana legacy — su contenido vive ahora en la ruta canónica `/dinero/suscripciones`
 * (Paso 7, nav canónico). Redirect permanente para no romper deep-links viejos.
 */
export default function Page() {
  redirect("/dinero/suscripciones");
}
