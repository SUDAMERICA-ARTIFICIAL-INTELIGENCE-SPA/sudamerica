-- 008_sucursales.sql — Multi-Sucursal (Multi-Location) support
-- Phase 1: Schema + FK columns on per-location tables

-- ─── Main sucursales table ──────────────────────────────────────────────────
CREATE TABLE sucursales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    direccion TEXT,
    telefono VARCHAR(50),
    horario JSONB DEFAULT '{}'::jsonb,
    zona_delivery TEXT,
    latitud NUMERIC(10, 7),
    longitud NUMERIC(10, 7),
    config JSONB DEFAULT '{}'::jsonb,
    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, slug),
    UNIQUE(tenant_id, nombre)
);

-- RLS
ALTER TABLE sucursales ENABLE ROW LEVEL SECURITY;
ALTER TABLE sucursales FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sucursales FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- Solo 1 principal activa por tenant
CREATE UNIQUE INDEX uq_sucursales_principal
    ON sucursales(tenant_id) WHERE es_principal = true AND activo = true;

CREATE INDEX idx_sucursales_tenant_activo ON sucursales(tenant_id, activo);

-- ─── Add sucursal_id FK to per-location tables ──────────────────────────────
ALTER TABLE mesas ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE comandas ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE reservaciones ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE ventas ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE evolution_instances ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE leads ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE sessions ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);

-- agente_config: de UNIQUE(tenant_id) a UNIQUE(tenant_id, sucursal_id)
ALTER TABLE agente_config DROP CONSTRAINT IF EXISTS uq_agente_config_tenant_id;
ALTER TABLE agente_config ADD COLUMN sucursal_id UUID REFERENCES sucursales(id);
ALTER TABLE agente_config ADD CONSTRAINT uq_agente_config_tenant_sucursal
    UNIQUE (tenant_id, sucursal_id);

-- mesas: de UNIQUE(tenant_id, numero) a UNIQUE(tenant_id, sucursal_id, numero)
ALTER TABLE mesas DROP CONSTRAINT IF EXISTS mesas_tenant_id_numero_key;
ALTER TABLE mesas DROP CONSTRAINT IF EXISTS uq_mesa_tenant_numero;
ALTER TABLE mesas ADD CONSTRAINT uq_mesas_tenant_sucursal_numero
    UNIQUE (tenant_id, sucursal_id, numero);

-- ─── Partial indexes (solo filas con sucursal asignada) ─────────────────────
CREATE INDEX idx_leads_sucursal ON leads(sucursal_id) WHERE sucursal_id IS NOT NULL;
CREATE INDEX idx_comandas_sucursal ON comandas(sucursal_id) WHERE sucursal_id IS NOT NULL;
CREATE INDEX idx_ventas_sucursal ON ventas(sucursal_id) WHERE sucursal_id IS NOT NULL;
CREATE INDEX idx_mesas_sucursal ON mesas(sucursal_id) WHERE sucursal_id IS NOT NULL;
CREATE INDEX idx_evolution_instances_sucursal ON evolution_instances(sucursal_id) WHERE sucursal_id IS NOT NULL;

-- ─── Price overrides per sucursal (schema now, logic later) ─────────────────
CREATE TABLE sucursal_producto_precios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sucursal_id UUID NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
    producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    precio NUMERIC(12, 2) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, sucursal_id, producto_id)
);

ALTER TABLE sucursal_producto_precios ENABLE ROW LEVEL SECURITY;
ALTER TABLE sucursal_producto_precios FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sucursal_producto_precios FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

CREATE INDEX idx_spp_sucursal_producto ON sucursal_producto_precios(sucursal_id, producto_id);
