-- 007_mesas_roles.sql
-- Adds mesas table, new plan tiers (ESTANDAR/PLUS), and PERSONAL role.

-- Mesas table
CREATE TABLE IF NOT EXISTS mesas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    numero INTEGER NOT NULL,
    nombre VARCHAR(100),
    capacidad INTEGER NOT NULL DEFAULT 4,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, numero)
);

-- RLS
ALTER TABLE mesas ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON mesas FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- Update existing FREE plans to ESTANDAR
UPDATE tenants SET plan = 'ESTANDAR' WHERE plan = 'FREE';

-- Migrate ASESOR/VIEWER roles to PERSONAL
UPDATE usuarios SET role = 'PERSONAL' WHERE role IN ('ASESOR', 'VIEWER');
