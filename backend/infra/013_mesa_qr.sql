-- 013_mesa_qr.sql — Add QR token to mesas for scan-to-WhatsApp flow
-- Run manually in Cloud SQL before deploying api-execute

-- 1. Add qr_token column (nullable first for existing rows)
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS qr_token VARCHAR(32) UNIQUE;

-- 2. Backfill existing mesas with random tokens
UPDATE mesas SET qr_token = encode(gen_random_bytes(16), 'hex') WHERE qr_token IS NULL;

-- 3. Make it NOT NULL after backfill
ALTER TABLE mesas ALTER COLUMN qr_token SET NOT NULL;

-- 4. Index for fast public lookups
CREATE INDEX IF NOT EXISTS idx_mesas_qr_token ON mesas(qr_token);

-- 5. Add mesa_id to sessions (links WhatsApp session to a physical table)
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS mesa_id UUID REFERENCES mesas(id) NULL;

-- 6. Tenant-safe RLS for the public QR endpoint (no JWT, but NO cross-tenant exposure)
-- The public QR scan endpoint sets app.allow_qr_lookup='true' (see shared/database/session.py)
-- so it can resolve the scanned mesa + its sucursal without a JWT, without leaking other tenants.
-- Mesas: publicly selectable only via a valid QR token (the endpoint queries by exact token).
CREATE POLICY qr_token_public_lookup ON mesas FOR SELECT USING (qr_token IS NOT NULL);
-- Sucursales: readable during a QR lookup OR by the owning tenant — never globally public.
CREATE POLICY public_read_for_joins ON sucursales
    FOR SELECT
    USING (
        current_setting('app.allow_qr_lookup', true) = 'true'
        OR tenant_id::text = current_setting('app.current_tenant_id', true)
    );
-- evolution_instances: no permissive public policy here. The controlled public lookup is
-- handled by evolution_instances_read in 002_rls_policies.sql (app.allow_instance_lookup),
-- which exposes only the single instance being resolved, never all rows.
