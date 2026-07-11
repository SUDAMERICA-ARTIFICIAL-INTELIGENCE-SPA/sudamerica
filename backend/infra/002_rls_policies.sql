-- ============================================================
-- Sudamérica AI: Row-Level Security by tenant_id
-- Canonical tenant context: current_setting('app.current_tenant_id')
-- ============================================================

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON usuarios;
CREATE POLICY tenant_isolation ON usuarios
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON categorias;
CREATE POLICY tenant_isolation ON categorias
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE productos FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON productos;
CREATE POLICY tenant_isolation ON productos
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON leads;
CREATE POLICY tenant_isolation ON leads
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE ventas ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON ventas;
CREATE POLICY tenant_isolation ON ventas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE agente_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE agente_config FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON agente_config;
CREATE POLICY tenant_isolation ON agente_config
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE revision_humana ENABLE ROW LEVEL SECURITY;
ALTER TABLE revision_humana FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON revision_humana;
CREATE POLICY tenant_isolation ON revision_humana
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON ai_conversations;
CREATE POLICY tenant_isolation ON ai_conversations
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE ai_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_embeddings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON ai_embeddings;
CREATE POLICY tenant_isolation ON ai_embeddings
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE smart_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE smart_alerts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON smart_alerts;
CREATE POLICY tenant_isolation ON smart_alerts
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE sales_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_targets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON sales_targets;
CREATE POLICY tenant_isolation ON sales_targets
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE evolution_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE evolution_instances FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON evolution_instances;
DROP POLICY IF EXISTS evolution_instances_read ON evolution_instances;
DROP POLICY IF EXISTS evolution_instances_write ON evolution_instances;
CREATE POLICY evolution_instances_read ON evolution_instances
    FOR SELECT
    USING (
        tenant_id::text = current_setting('app.current_tenant_id', true)
        OR (
            current_setting('app.allow_instance_lookup', true) = 'true'
            AND instance_name = current_setting('app.current_instance_name', true)
        )
    );
CREATE POLICY evolution_instances_write ON evolution_instances
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE llm_provider_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_provider_keys FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON llm_provider_keys;
CREATE POLICY tenant_isolation ON llm_provider_keys
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE task_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON task_logs;
CREATE POLICY tenant_isolation ON task_logs
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON contacts;
CREATE POLICY tenant_isolation ON contacts
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON sessions;
CREATE POLICY tenant_isolation ON sessions
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE tenant_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_knowledge FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tenant_knowledge;
CREATE POLICY tenant_isolation ON tenant_knowledge
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- mesas
ALTER TABLE mesas ENABLE ROW LEVEL SECURITY;
ALTER TABLE mesas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON mesas;
CREATE POLICY tenant_isolation ON mesas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- modifier_groups
ALTER TABLE modifier_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifier_groups FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON modifier_groups;
CREATE POLICY tenant_isolation ON modifier_groups
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- modifiers
ALTER TABLE modifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifiers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON modifiers;
CREATE POLICY tenant_isolation ON modifiers
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- comandas
ALTER TABLE comandas ENABLE ROW LEVEL SECURITY;
ALTER TABLE comandas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON comandas;
CREATE POLICY tenant_isolation ON comandas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
