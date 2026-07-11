-- Suministros (raw ingredients) + Recetas (product-ingredient link)

CREATE TABLE IF NOT EXISTS suministros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    nombre VARCHAR(255) NOT NULL,
    unidad VARCHAR(50) NOT NULL DEFAULT 'unidad',  -- kg, litro, unidad, gramo
    stock_actual NUMERIC(12,2) NOT NULL DEFAULT 0,
    stock_minimo NUMERIC(12,2) NOT NULL DEFAULT 0,
    costo_unitario NUMERIC(12,2),
    proveedor VARCHAR(255),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recetas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    producto_id UUID NOT NULL REFERENCES productos(id),
    suministro_id UUID NOT NULL REFERENCES suministros(id),
    cantidad_necesaria NUMERIC(12,4) NOT NULL,  -- e.g., 0.200 kg of flour per pizza
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, producto_id, suministro_id)
);

-- RLS policies
ALTER TABLE suministros ENABLE ROW LEVEL SECURITY;
ALTER TABLE recetas ENABLE ROW LEVEL SECURITY;

CREATE POLICY suministros_tenant ON suministros
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY recetas_tenant ON recetas
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_suministros_tenant ON suministros(tenant_id);
CREATE INDEX IF NOT EXISTS idx_recetas_tenant_producto ON recetas(tenant_id, producto_id);
CREATE INDEX IF NOT EXISTS idx_recetas_tenant_suministro ON recetas(tenant_id, suministro_id);
