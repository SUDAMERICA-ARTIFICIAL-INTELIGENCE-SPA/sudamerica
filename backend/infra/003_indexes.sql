-- ============================================================
-- Sudamérica AI: performance and uniqueness indexes
-- ============================================================

-- usuarios
CREATE INDEX idx_usuarios_tenant_email ON usuarios(tenant_id, email);
CREATE INDEX idx_usuarios_tenant_role ON usuarios(tenant_id, role);
CREATE INDEX idx_usuarios_tenant_activo ON usuarios(tenant_id, activo);

-- categorias
CREATE INDEX idx_categorias_tenant_activo ON categorias(tenant_id, activo);

-- productos
CREATE INDEX idx_productos_tenant_activo ON productos(tenant_id, activo);
CREATE INDEX idx_productos_tenant_categoria ON productos(tenant_id, categoria_id);
CREATE INDEX idx_productos_tenant_precio ON productos(tenant_id, precio);
CREATE INDEX idx_productos_nombre_search ON productos(tenant_id, nombre varchar_pattern_ops);

-- leads
CREATE INDEX idx_leads_tenant_estado ON leads(tenant_id, estado);
CREATE INDEX idx_leads_tenant_canal ON leads(tenant_id, canal);
CREATE INDEX idx_leads_tenant_asignado ON leads(tenant_id, asignado_a);
CREATE INDEX idx_leads_tenant_created ON leads(tenant_id, created_at DESC);
CREATE INDEX idx_leads_tenant_activo ON leads(tenant_id, activo);
CREATE INDEX idx_leads_tenant_sector ON leads(tenant_id, sector);

-- ventas
CREATE INDEX idx_ventas_tenant_created ON ventas(tenant_id, created_at DESC);
CREATE INDEX idx_ventas_tenant_producto ON ventas(tenant_id, producto_id);
CREATE INDEX idx_ventas_tenant_usuario ON ventas(tenant_id, usuario_id);

-- agente_config
CREATE INDEX idx_agente_config_tenant ON agente_config(tenant_id);

-- revision_humana
CREATE INDEX idx_revision_tenant_procesado ON revision_humana(tenant_id, procesado);
CREATE INDEX idx_revision_tenant_created ON revision_humana(tenant_id, created_at DESC);
CREATE INDEX idx_revision_tenant_activo_procesado ON revision_humana(tenant_id, activo, procesado);

-- ai_conversations
CREATE INDEX idx_ai_conv_tenant_lead ON ai_conversations(tenant_id, lead_id);
CREATE INDEX idx_ai_conv_tenant_created ON ai_conversations(tenant_id, created_at DESC);
CREATE INDEX idx_ai_conv_session ON ai_conversations(session_id);

-- ai_embeddings
CREATE INDEX idx_ai_embeddings_tenant ON ai_embeddings(tenant_id);
CREATE INDEX idx_ai_embeddings_source ON ai_embeddings(tenant_id, source_type, source_id);
CREATE INDEX idx_ai_embeddings_vector ON ai_embeddings USING hnsw (embedding vector_cosine_ops);

-- smart_alerts
CREATE INDEX idx_smart_alerts_tenant_leido_created ON smart_alerts(tenant_id, leido, created_at DESC);

-- sales_targets
CREATE INDEX idx_sales_targets_tenant_periodo ON sales_targets(tenant_id, periodo);
CREATE UNIQUE INDEX uq_sales_targets_team_period ON sales_targets(tenant_id, periodo) WHERE asesor_id IS NULL;
CREATE UNIQUE INDEX uq_sales_targets_advisor_period ON sales_targets(tenant_id, asesor_id, periodo) WHERE asesor_id IS NOT NULL;

-- evolution_instances
CREATE INDEX idx_evolution_instances_tenant_activo ON evolution_instances(tenant_id, activo);

-- llm_provider_keys
CREATE INDEX idx_llm_provider_keys_tenant_activo ON llm_provider_keys(tenant_id, activo);

-- contacts
CREATE INDEX idx_contacts_tenant_phone ON contacts(tenant_id, phone);
CREATE INDEX idx_contacts_tenant_activo ON contacts(tenant_id, activo);

-- sessions
CREATE INDEX idx_sessions_tenant_contact_status ON sessions(tenant_id, contact_id, status);
CREATE INDEX idx_sessions_tenant_status ON sessions(tenant_id, status);
CREATE INDEX idx_sessions_tenant_created ON sessions(tenant_id, created_at DESC);

-- tenant_knowledge
CREATE INDEX idx_tenant_knowledge_tenant_type ON tenant_knowledge(tenant_id, type);
CREATE INDEX idx_tenant_knowledge_tenant_priority ON tenant_knowledge(tenant_id, priority DESC);

-- task_logs
CREATE INDEX idx_task_logs_tenant_estado ON task_logs(tenant_id, estado);
CREATE INDEX idx_task_logs_tenant_created ON task_logs(tenant_id, created_at DESC);

-- mesas
CREATE INDEX idx_mesas_tenant_activo ON mesas(tenant_id, activo);

-- modifier_groups
CREATE INDEX idx_modifier_groups_tenant_activo ON modifier_groups(tenant_id, activo);

-- modifiers
CREATE INDEX idx_modifiers_tenant_activo ON modifiers(tenant_id, activo);
CREATE INDEX idx_modifiers_grupo ON modifiers(grupo_id);

-- producto_modifier_groups
CREATE INDEX idx_pmg_producto ON producto_modifier_groups(producto_id);
CREATE INDEX idx_pmg_modifier_group ON producto_modifier_groups(modifier_group_id);

-- comandas
CREATE INDEX idx_comandas_tenant_estado ON comandas(tenant_id, estado);
CREATE INDEX idx_comandas_tenant_created ON comandas(tenant_id, created_at DESC);
CREATE INDEX idx_comandas_tenant_cliente ON comandas(tenant_id, cliente_id);
CREATE INDEX idx_comandas_tenant_venta ON comandas(tenant_id, venta_id);

-- comanda_items
CREATE INDEX idx_comanda_items_comanda ON comanda_items(comanda_id);
CREATE INDEX idx_comanda_items_producto ON comanda_items(producto_id);

-- platform_config (no tenant scope — small table, key is UNIQUE)

-- api_key_audit
CREATE INDEX idx_api_key_audit_created ON api_key_audit(created_at DESC);
CREATE INDEX idx_api_key_audit_provider ON api_key_audit(provider);
