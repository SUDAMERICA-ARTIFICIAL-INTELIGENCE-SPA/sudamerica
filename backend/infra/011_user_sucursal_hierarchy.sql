-- 011_user_sucursal_hierarchy.sql
-- Adds sucursal_id to usuarios and location fields to sucursales.
-- Enables per-branch user scoping: Restaurant → Sucursales → Users

-- A) sucursal_id on usuarios (nullable = admin global del restaurant)
ALTER TABLE usuarios ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
CREATE INDEX idx_usuarios_sucursal ON usuarios(sucursal_id) WHERE sucursal_id IS NOT NULL;

-- B) Location fields on sucursales
ALTER TABLE sucursales ADD COLUMN ciudad VARCHAR(100);
ALTER TABLE sucursales ADD COLUMN region VARCHAR(100);
ALTER TABLE sucursales ADD COLUMN codigo_postal VARCHAR(20);
ALTER TABLE sucursales ADD COLUMN pais VARCHAR(3) NOT NULL DEFAULT 'CL';
ALTER TABLE sucursales ADD COLUMN google_maps_url TEXT;

-- C) Composite constraint for safe FK (same tenant)
ALTER TABLE sucursales ADD CONSTRAINT uq_sucursales_tenant_id_id UNIQUE (tenant_id, id);
ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_sucursal_tenant
    FOREIGN KEY (tenant_id, sucursal_id) REFERENCES sucursales(tenant_id, id) ON DELETE SET NULL;
