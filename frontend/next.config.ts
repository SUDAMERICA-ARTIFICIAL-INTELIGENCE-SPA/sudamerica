import path from "node:path";
import type { NextConfig } from "next";

// ── Modo de build ────────────────────────────────────────────────────────────
// Por defecto la app se construye como `output: "standalone"` (deploy real con
// backend Python + DB). Cuando `STATIC_EXPORT=1`, se cambia a un export estático
// de la VITRINA (showroom) para GitHub Pages: sin servidor, servido bajo el
// subpath `/sudamerica`. El default NO se toca — `npm run build` normal sigue
// generando el standalone.
const STATIC_EXPORT = process.env.STATIC_EXPORT === "1";
const BASE_PATH = STATIC_EXPORT ? "/sudamerica" : "";

const base: NextConfig = {
  outputFileTracingRoot: path.resolve(__dirname, ".."),
  reactStrictMode: true,
  // Overlay de dev de Next (círculo abajo-izquierda). Único flag soportado en 15.5:
  // los sub-flags appIsrStatus/buildActivity están deprecados y no lo apagan.
  devIndicators: false,
  experimental: {
    optimizePackageImports: ["@mantine/core", "@mantine/hooks", "@tabler/icons-react"],
  },
  // Expuesto al cliente para prefijar hrefs de HTML crudo (favicon) que Next no
  // reescribe automáticamente con basePath. Vacío en el build real.
  env: { NEXT_PUBLIC_BASE_PATH: BASE_PATH },
};

const nextConfig: NextConfig = STATIC_EXPORT
  ? {
      ...base,
      output: "export",
      basePath: BASE_PATH,
      assetPrefix: `${BASE_PATH}/`,
      // Pages no tiene el optimizador de imágenes de Next → sirve <img> tal cual.
      images: { unoptimized: true },
      // URLs con slash final ⇒ cada ruta es `<ruta>/index.html`: evita los
      // redirects 3xx que Pages no puede emitir para rutas anidadas.
      trailingSlash: true,
    }
  : { ...base, output: "standalone" };

export default nextConfig;
