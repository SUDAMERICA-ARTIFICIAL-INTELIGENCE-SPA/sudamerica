-- ============================================================
-- Quality gate remediation indexes (2026-03-15)
-- Gate E: Performance — cover all frequently filtered/joined columns
--
-- NOTE: Use CREATE INDEX CONCURRENTLY in production to avoid
-- table locks. Remove CONCURRENTLY for initial schema setup.
-- ============================================================

-- revision_humana: operador lookups (admin N+1 fix)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revision_humana_operador
  ON revision_humana(tenant_id, operador_id);

-- ai_conversations: usuario lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_conv_usuario
  ON ai_conversations(tenant_id, usuario_id);

-- smart_alerts: lead_id joins
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smart_alerts_lead
  ON smart_alerts(tenant_id, lead_id);

-- sessions: lead_id lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_lead
  ON sessions(tenant_id, lead_id);

-- tenants: plan + activo for admin metrics (Gate E — P0-4)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_plan_activo
  ON tenants(plan, activo);

-- evolution_instances: status for admin metrics overview
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evolution_instances_status
  ON evolution_instances(status);

-- evolution_instances: created_at for admin list ordering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evolution_instances_created
  ON evolution_instances(created_at DESC);

-- llm_provider_keys: created_at for admin list ordering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_llm_provider_keys_created
  ON llm_provider_keys(created_at DESC);

-- leads: fidelización columns for customer segmentation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_estado_cliente
  ON leads(tenant_id, estado_cliente);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_ultima_visita
  ON leads(tenant_id, ultima_visita DESC);

-- productos: disponible filter (menu display)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productos_disponible
  ON productos(tenant_id, disponible) WHERE disponible = true;

-- ai_conversations: external_wa_id for WhatsApp message dedup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_conv_external_wa
  ON ai_conversations(external_wa_id) WHERE external_wa_id IS NOT NULL;

-- ventas: tipo_entrega for delivery/dine-in reports
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ventas_tipo_entrega
  ON ventas(tenant_id, tipo_entrega);

-- comandas: tenant + estado for KDS queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comandas_tenant_estado
  ON comandas(tenant_id, estado);

-- comandas: fecha range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comandas_tenant_created
  ON comandas(tenant_id, created_at DESC);

-- comanda_items: comanda_id for JOIN performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comanda_items_comanda
  ON comanda_items(comanda_id);

-- modifier_groups: tenant + activo
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_modifier_groups_tenant_activo
  ON modifier_groups(tenant_id, activo);

-- producto_modifier_groups: product lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pmg_producto
  ON producto_modifier_groups(producto_id);
