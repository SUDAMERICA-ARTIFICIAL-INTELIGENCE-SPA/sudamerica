-- 025: F6 multi-rubro — sub-entidad del cliente (mascota/vehículo/propiedad/paciente)
-- Tabla nueva, aditiva, gateada por el módulo SUB_ENTIDAD del rubro.
-- down: DROP TABLE IF EXISTS cliente_subentidades;

CREATE TABLE IF NOT EXISTS cliente_subentidades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL,          -- mascota / vehiculo / propiedad / paciente
    nombre VARCHAR(255) NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}',  -- atributos por rubro (raza, patente, m2, ...)
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subentidades_tenant_lead
    ON cliente_subentidades(tenant_id, lead_id);

-- RLS: replica el patrón tenant_isolation (002_rls_policies.sql)
ALTER TABLE cliente_subentidades ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON cliente_subentidades;
CREATE POLICY tenant_isolation ON cliente_subentidades
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
