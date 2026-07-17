import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
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
  env: { NEXT_PUBLIC_BASE_PATH: "" },
};

export default nextConfig;
