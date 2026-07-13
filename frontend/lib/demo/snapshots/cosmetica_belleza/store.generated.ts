// GENERADO por tools/snapshot_demo_fixtures.mjs — NO editar a mano.
// Snapshots reales del rubro cosmetica_belleza (aura-demo) capturados del backend seedeado.
import type { SnapshotEntry } from "@/lib/demo/snapshot-types";
import s_auth_me from "./auth-me.json";
import s_tenants_me from "./tenants-me.json";
import s_rubros_disponibles from "./rubros-disponibles.json";
import s_metricas_dashboard from "./metricas-dashboard.json";
import s_metricas_revenue from "./metricas-revenue.json";
import s_metricas_operativo from "./metricas-operativo.json";
import s_metricas_financiero from "./metricas-financiero.json";
import s_metricas_productos_top from "./metricas-productos-top.json";
import s_metricas_weekly_activity from "./metricas-weekly-activity.json";
import s_metricas_menu_engineering from "./metricas-menu-engineering.json";
import s_metricas_conversion from "./metricas-conversion.json";
import s_metricas_leads_estado from "./metricas-leads-estado.json";
import s_metricas_por_sector from "./metricas-por-sector.json";
import s_metricas_actividad from "./metricas-actividad.json";
import s_metricas_cobros from "./metricas-cobros.json";
import s_metricas_tesoreria from "./metricas-tesoreria.json";
import s_metricas_flujo_caja from "./metricas-flujo-caja.json";
import s_metricas_por_canal from "./metricas-por-canal.json";
import s_metricas_segmentacion_clientes from "./metricas-segmentacion-clientes.json";
import s_metricas_loyalty_insights from "./metricas-loyalty-insights.json";
import s_categorias from "./categorias.json";
import s_productos from "./productos.json";
import s_modifier_groups from "./modifier-groups.json";
import s_suministros from "./suministros.json";
import s_suministros_recetas from "./suministros-recetas.json";
import s_ventas from "./ventas.json";
import s_comandas from "./comandas.json";
import s_comandas_kds from "./comandas-kds.json";
import s_mesas from "./mesas.json";
import s_reservaciones from "./reservaciones.json";
import s_sales_targets from "./sales-targets.json";
import s_compras_resumen from "./compras-resumen.json";
import s_compras_ordenes from "./compras-ordenes.json";
import s_compras_facturas from "./compras-facturas.json";
import s_compras_proveedores from "./compras-proveedores.json";
import s_compras_recepciones from "./compras-recepciones.json";
import s_compras_requisiciones from "./compras-requisiciones.json";
import s_compras_cotizaciones from "./compras-cotizaciones.json";
import s_compras_evaluacion from "./compras-evaluacion.json";
import s_inventario_movimientos from "./inventario-movimientos.json";
import s_leads from "./leads.json";
import s_campanas from "./campanas.json";
import s_devoluciones from "./devoluciones.json";
import s_ai_conversations from "./ai-conversations.json";
import s_ai_config from "./ai-config.json";
import s_ai_conversations_list from "./ai-conversations-list.json";
import s_ai_knowledge from "./ai-knowledge.json";
import s_alertas from "./alertas.json";
import s_plantillas from "./plantillas.json";
import s_documentos from "./documentos.json";
import s_usuarios from "./usuarios.json";
import s_sucursales from "./sucursales.json";
import s_billing_usage from "./billing-usage.json";
import s_menu_import_history from "./menu-import-history.json";
import s_sudamerica_history from "./sudamerica-history.json";
import s_leads_detail from "./leads-detail.json";
import s_productos_detail from "./productos-detail.json";
import s_ventas_detail from "./ventas-detail.json";
import s_compras_ordenes_detail from "./compras-ordenes-detail.json";

export const COSMETICA_SNAPSHOTS: readonly SnapshotEntry[] = [
  { serve: "/auth/me", query: null, data: s_auth_me as unknown },
  { serve: "/tenants/me", query: null, data: s_tenants_me as unknown },
  { serve: "/rubros/disponibles", query: null, data: s_rubros_disponibles as unknown },
  { serve: "/metricas/dashboard", query: null, data: s_metricas_dashboard as unknown },
  { serve: "/metricas/revenue", query: null, data: s_metricas_revenue as unknown },
  { serve: "/metricas/operativo", query: null, data: s_metricas_operativo as unknown },
  { serve: "/metricas/financiero", query: null, data: s_metricas_financiero as unknown },
  { serve: "/metricas/productos-top", query: "limit=10", data: s_metricas_productos_top as unknown },
  { serve: "/metricas/weekly-activity", query: null, data: s_metricas_weekly_activity as unknown },
  { serve: "/metricas/menu-engineering", query: null, data: s_metricas_menu_engineering as unknown },
  { serve: "/metricas/conversion", query: null, data: s_metricas_conversion as unknown },
  { serve: "/metricas/leads-estado", query: null, data: s_metricas_leads_estado as unknown },
  { serve: "/metricas/por-sector", query: null, data: s_metricas_por_sector as unknown },
  { serve: "/metricas/actividad", query: null, data: s_metricas_actividad as unknown },
  { serve: "/metricas/cobros", query: null, data: s_metricas_cobros as unknown },
  { serve: "/metricas/tesoreria", query: null, data: s_metricas_tesoreria as unknown },
  { serve: "/metricas/flujo-caja", query: null, data: s_metricas_flujo_caja as unknown },
  { serve: "/metricas/por-canal", query: null, data: s_metricas_por_canal as unknown },
  { serve: "/metricas/segmentacion-clientes", query: null, data: s_metricas_segmentacion_clientes as unknown },
  { serve: "/metricas/loyalty-insights", query: null, data: s_metricas_loyalty_insights as unknown },
  { serve: "/categorias", query: null, data: s_categorias as unknown },
  { serve: "/productos", query: "page=1&page_size=100", data: s_productos as unknown },
  { serve: "/modifier-groups", query: null, data: s_modifier_groups as unknown },
  { serve: "/suministros", query: null, data: s_suministros as unknown },
  { serve: "/suministros/recetas", query: null, data: s_suministros_recetas as unknown },
  { serve: "/ventas", query: "page=1&page_size=100", data: s_ventas as unknown },
  { serve: "/comandas", query: "page=1&page_size=100", data: s_comandas as unknown },
  { serve: "/comandas/kds", query: null, data: s_comandas_kds as unknown },
  { serve: "/mesas", query: null, data: s_mesas as unknown },
  { serve: "/reservaciones", query: "page=1&page_size=100", data: s_reservaciones as unknown },
  { serve: "/sales-targets", query: null, data: s_sales_targets as unknown },
  { serve: "/compras/resumen", query: null, data: s_compras_resumen as unknown },
  { serve: "/compras/ordenes", query: "page=1&page_size=100", data: s_compras_ordenes as unknown },
  { serve: "/compras/facturas", query: "page=1&page_size=100", data: s_compras_facturas as unknown },
  { serve: "/compras/proveedores", query: "page=1&page_size=100", data: s_compras_proveedores as unknown },
  { serve: "/compras/recepciones", query: "page=1&page_size=100", data: s_compras_recepciones as unknown },
  { serve: "/compras/requisiciones", query: "page=1&page_size=100", data: s_compras_requisiciones as unknown },
  { serve: "/compras/cotizaciones", query: "page=1&page_size=100", data: s_compras_cotizaciones as unknown },
  { serve: "/compras/evaluacion", query: null, data: s_compras_evaluacion as unknown },
  { serve: "/inventario/movimientos", query: "page=1&page_size=100", data: s_inventario_movimientos as unknown },
  { serve: "/leads", query: "page=1&page_size=100", data: s_leads as unknown },
  { serve: "/campanas", query: null, data: s_campanas as unknown },
  { serve: "/devoluciones", query: "page=1&page_size=100", data: s_devoluciones as unknown },
  { serve: "/ai-conversations", query: "page=1&page_size=100", data: s_ai_conversations as unknown },
  { serve: "/config", query: null, data: s_ai_config as unknown },
  { serve: "/conversations", query: "page=1&page_size=100", data: s_ai_conversations_list as unknown },
  { serve: "/knowledge", query: null, data: s_ai_knowledge as unknown },
  { serve: "/alertas", query: "page=1&page_size=100", data: s_alertas as unknown },
  { serve: "/plantillas", query: null, data: s_plantillas as unknown },
  { serve: "/documentos", query: "page=1&page_size=100", data: s_documentos as unknown },
  { serve: "/usuarios", query: null, data: s_usuarios as unknown },
  { serve: "/sucursales", query: null, data: s_sucursales as unknown },
  { serve: "/billing/usage", query: null, data: s_billing_usage as unknown },
  { serve: "/menu/import/history", query: null, data: s_menu_import_history as unknown },
  { serve: "/sudamerica/history", query: null, data: s_sudamerica_history as unknown },
  { serve: "/leads/{id}", query: null, data: s_leads_detail as unknown },
  { serve: "/productos/{id}", query: null, data: s_productos_detail as unknown },
  { serve: "/ventas/{id}", query: null, data: s_ventas_detail as unknown },
  { serve: "/compras/ordenes/{id}", query: null, data: s_compras_ordenes_detail as unknown },
];
