// Sector-specific field definitions, KPIs, and LATAM benchmarks

export type Sector =
  | "salud_estetica"
  | "inmobiliario"
  | "automotriz"
  | "gastronomia"
  | "educacion"
  | "mascotas"
  | "retail"
  | "b2b"
  | "turismo"
  | "otro";

export interface SectorField {
  key: string;
  label: string;
  type: "text" | "number" | "boolean" | "select";
  options?: readonly string[];
  required: boolean;
}

export interface SectorBenchmark {
  metric: string;
  value: string;
  description: string;
}

export interface SectorConfig {
  label: string;
  primaryKpi: string;
  fields: readonly SectorField[];
  benchmarks: readonly SectorBenchmark[];
}

export const SECTOR_CONFIG: Record<Sector, SectorConfig> = {
  salud_estetica: {
    label: "Salud / Estética",
    primaryKpi: "Tasa No-Show",
    fields: [
      { key: "especialidad", label: "Especialidad", type: "text", required: false },
      { key: "tipo_servicio", label: "Tipo de servicio", type: "text", required: false },
    ],
    benchmarks: [
      { metric: "FCR", value: "75-85%", description: "First Contact Resolution" },
      { metric: "Ciclo de Venta", value: "<48h", description: "Tiempo promedio de cierre" },
    ],
  },
  inmobiliario: {
    label: "Inmobiliario",
    primaryKpi: "Días hasta Cierre",
    fields: [
      {
        key: "tipo_propiedad",
        label: "Tipo de propiedad",
        type: "select",
        options: ["Casa", "Depto", "Local", "Terreno"] as const,
        required: false,
      },
      {
        key: "operacion",
        label: "Operación",
        type: "select",
        options: ["Venta", "Alquiler"] as const,
        required: false,
      },
      { key: "zona", label: "Zona", type: "text", required: false },
    ],
    benchmarks: [
      {
        metric: "Ciclo de Venta",
        value: "60-120 días",
        description: "Tiempo promedio hasta escritura",
      },
      { metric: "Retención Alquiler", value: "70-80%", description: "Renovación de contrato" },
    ],
  },
  automotriz: {
    label: "Automotriz",
    primaryKpi: "Test-Drive Conversion",
    fields: [
      { key: "marca", label: "Marca", type: "text", required: false },
      { key: "modelo_interes", label: "Modelo de interés", type: "text", required: false },
    ],
    benchmarks: [
      { metric: "Test-Drive Rate", value: "20-35%", description: "Leads que llegan a test drive" },
    ],
  },
  gastronomia: {
    label: "Gastronomía",
    primaryKpi: "Recurrencia de Compra",
    fields: [
      {
        key: "tipo_pedido",
        label: "Tipo de pedido",
        type: "select",
        options: ["Delivery", "Mesa", "Takeaway"] as const,
        required: false,
      },
    ],
    benchmarks: [
      {
        metric: "Recurrencia 30d",
        value: "30-45%",
        description: "Clientes que repiten en 30 días",
      },
    ],
  },
  educacion: {
    label: "Educación",
    primaryKpi: "Enrollment Velocity",
    fields: [
      {
        key: "modalidad",
        label: "Modalidad",
        type: "select",
        options: ["Online", "Presencial", "Híbrido"] as const,
        required: false,
      },
      { key: "programa", label: "Programa", type: "text", required: false },
    ],
    benchmarks: [
      { metric: "Asistencia Webinar", value: "40-55%", description: "Tasa de asistencia a demos" },
    ],
  },
  mascotas: {
    label: "Mascotas",
    primaryKpi: "Predictive Restock",
    fields: [{ key: "tipo_mascota", label: "Tipo de mascota", type: "text", required: false }],
    benchmarks: [
      { metric: "Predicción Reposición", value: ">25%", description: "Pedidos proactivos por IA" },
    ],
  },
  retail: {
    label: "Retail",
    primaryKpi: "Carritos Recuperados IA",
    fields: [{ key: "categoria_producto", label: "Categoría", type: "text", required: false }],
    benchmarks: [
      { metric: "Cart Recovery", value: "15-25%", description: "Carritos abandonados recuperados" },
      { metric: "WA Conversion", value: ">12%", description: "Conversión vía WhatsApp" },
    ],
  },
  b2b: {
    label: "B2B",
    primaryKpi: "Win Rate Propuestas",
    fields: [
      { key: "industria", label: "Industria", type: "text", required: false },
      {
        key: "tamanio_empresa",
        label: "Tamaño empresa",
        type: "select",
        options: ["1-10", "11-50", "51-200", "200+"] as const,
        required: false,
      },
    ],
    benchmarks: [{ metric: "Win Rate", value: "20-35%", description: "Propuestas que cierran" }],
  },
  turismo: {
    label: "Turismo",
    primaryKpi: "Booking Lead Time",
    fields: [
      {
        key: "tipo_viaje",
        label: "Tipo de viaje",
        type: "select",
        options: ["Nacional", "Internacional", "Crucero"] as const,
        required: false,
      },
    ],
    benchmarks: [{ metric: "WA ROI", value: "hasta 16x", description: "ROI vs OTAs por WhatsApp" }],
  },
  otro: {
    label: "Otro",
    primaryKpi: "Conversión",
    fields: [],
    benchmarks: [],
  },
};

export function getSectorConfig(sector: Sector): SectorConfig {
  return SECTOR_CONFIG[sector];
}

export const SECTOR_OPTIONS = Object.entries(SECTOR_CONFIG).map(([key, config]) => ({
  value: key as Sector,
  label: config.label,
}));
