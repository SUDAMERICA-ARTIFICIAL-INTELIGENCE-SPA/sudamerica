-- ============================================================
-- 005_resto_fase1.sql — Sudamérica AI Resto Phase 1: Modifiers + Comandas
-- Execute manually in Cloud SQL (no auto-migrate)
-- ============================================================

-- 1. Modifier Groups
CREATE TABLE modifier_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('SINGLE_SELECT', 'MULTI_SELECT')),
    obligatorio BOOLEAN DEFAULT false,
    max_selecciones INT DEFAULT NULL,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_modifier_groups_tenant ON modifier_groups(tenant_id);

-- 2. Modifiers (options within groups)
CREATE TABLE modifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    grupo_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    precio_delta DECIMAL(10,2) DEFAULT 0,
    activo BOOLEAN DEFAULT true,
    orden INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_modifiers_tenant ON modifiers(tenant_id);
CREATE INDEX idx_modifiers_grupo ON modifiers(grupo_id);

-- 3. Product ↔ Modifier Group (M:N)
CREATE TABLE producto_modifier_groups (
    producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    modifier_group_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (producto_id, modifier_group_id)
);

-- 4. Comandas (kitchen orders)
CREATE TABLE comandas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    venta_id UUID REFERENCES ventas(id),
    cliente_id UUID REFERENCES leads(id),
    tipo_entrega VARCHAR(20) NOT NULL CHECK (tipo_entrega IN ('MESA', 'DELIVERY', 'RETIRO')),
    numero_mesa INT,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE', 'EN_COCINA', 'LISTO', 'ENTREGADO', 'CANCELADO')),
    canal_origen VARCHAR(20) NOT NULL CHECK (canal_origen IN ('WHATSAPP', 'WEB', 'PRESENCIAL')),
    notas TEXT,
    prioridad INT DEFAULT 0,
    tiempo_estimado_min INT,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    entregado_at TIMESTAMPTZ
);

CREATE INDEX idx_comandas_tenant ON comandas(tenant_id);
CREATE INDEX idx_comandas_estado ON comandas(tenant_id, estado);
CREATE INDEX idx_comandas_cliente ON comandas(cliente_id);
CREATE INDEX idx_comandas_created ON comandas(tenant_id, created_at DESC);

-- 5. Comanda Items
CREATE TABLE comanda_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comanda_id UUID NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    producto_id UUID NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10,2) NOT NULL,
    modifiers_json JSONB DEFAULT '[]',
    subtotal DECIMAL(10,2) NOT NULL,
    notas TEXT
);

CREATE INDEX idx_comanda_items_comanda ON comanda_items(comanda_id);

-- 6. Add tipo_entrega and numero_mesa to ventas (for order context)
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20);
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS numero_mesa INT;

-- 7. RLS policies
ALTER TABLE modifier_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifier_groups FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON modifier_groups;
CREATE POLICY tenant_isolation ON modifier_groups
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE modifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifiers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON modifiers;
CREATE POLICY tenant_isolation ON modifiers
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE comandas ENABLE ROW LEVEL SECURITY;
ALTER TABLE comandas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON comandas;
CREATE POLICY tenant_isolation ON comandas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- producto_modifier_groups doesn't have tenant_id — access controlled via JOIN
-- comanda_items doesn't have tenant_id — access controlled via comanda FK
