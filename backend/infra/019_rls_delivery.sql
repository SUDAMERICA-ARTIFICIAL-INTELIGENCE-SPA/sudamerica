-- 019_rls_delivery.sql
-- Apply tenant RLS to delivery tables introduced after the canonical snapshot.

ALTER TABLE repartidores ENABLE ROW LEVEL SECURITY;
ALTER TABLE repartidores FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON repartidores;
CREATE POLICY tenant_isolation ON repartidores
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE delivery_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_assignments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON delivery_assignments;
CREATE POLICY tenant_isolation ON delivery_assignments
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
