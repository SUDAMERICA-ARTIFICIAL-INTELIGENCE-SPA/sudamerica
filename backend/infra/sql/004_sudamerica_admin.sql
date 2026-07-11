-- Sudamerica Admin: SUPERADMIN role + platform tables
-- Run manually in Cloud SQL before deploying sudamerica-admin

-- 1. Add SUPERADMIN role (safe: IF NOT EXISTS pattern for enums)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'SUPERADMIN' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE 'SUPERADMIN';
    END IF;
END $$;

-- 2. Platform config table (key-value store for global settings)
CREATE TABLE IF NOT EXISTS platform_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by UUID REFERENCES usuarios(id)
);

-- 3. API key audit log
CREATE TABLE IF NOT EXISTS api_key_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    performed_by UUID REFERENCES usuarios(id),
    old_key_masked VARCHAR(20),
    new_key_masked VARCHAR(20),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- No RLS on platform_config / api_key_audit (superadmin-only access)

-- 4. Superadmin RLS bypass policies
-- When app.is_superadmin = 'true', allow full cross-tenant SELECT access.
-- This is set by the get_db_admin dependency used in admin routes.

DO $$ DECLARE tbl TEXT; BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'usuarios','leads','categorias','productos','ventas',
    'agente_config','revision_humana','ai_conversations','ai_embeddings',
    'smart_alerts','sales_targets','evolution_instances','llm_provider_keys',
    'task_logs','contacts','sessions','tenant_knowledge'
  ] LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS superadmin_bypass ON %I; '
      'CREATE POLICY superadmin_bypass ON %I FOR ALL '
      'USING (current_setting(''app.is_superadmin'', true) = ''true'') '
      'WITH CHECK (current_setting(''app.is_superadmin'', true) = ''true'');',
      tbl, tbl
    );
  END LOOP;
END $$;
