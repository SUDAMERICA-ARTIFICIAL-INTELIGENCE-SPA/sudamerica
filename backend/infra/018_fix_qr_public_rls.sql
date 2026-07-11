-- 018_fix_qr_public_rls.sql
-- Restrict public QR RLS helpers so QR scans do not expose WhatsApp secrets.

ALTER TABLE sucursales ENABLE ROW LEVEL SECURITY;
ALTER TABLE sucursales FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read_for_joins ON sucursales;
CREATE POLICY public_read_for_joins ON sucursales
    FOR SELECT
    USING (
        current_setting('app.allow_qr_lookup', true) = 'true'
        OR tenant_id::text = current_setting('app.current_tenant_id', true)
    );

DROP POLICY IF EXISTS public_read_for_qr ON evolution_instances;
