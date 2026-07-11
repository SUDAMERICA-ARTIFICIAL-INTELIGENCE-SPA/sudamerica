-- 016_delivery_enhancements.sql
-- Driver pool, delivery assignments, and prep time for delivery coordination.

-- 1. Repartidores (driver pool per tenant)
CREATE TABLE IF NOT EXISTS repartidores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sucursal_id UUID REFERENCES sucursales(id),
    nombre VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, phone)
);
CREATE INDEX IF NOT EXISTS idx_repartidores_tenant ON repartidores(tenant_id, activo);

-- 2. Delivery assignments (one per comanda, atomic claim)
CREATE TABLE IF NOT EXISTS delivery_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    comanda_id UUID NOT NULL REFERENCES comandas(id) ON DELETE CASCADE UNIQUE,
    repartidor_id UUID REFERENCES repartidores(id),
    repartidor_phone VARCHAR(20),
    repartidor_nombre VARCHAR(100),
    estado VARCHAR(20) NOT NULL DEFAULT 'PUBLICADO',
    metodo_pago VARCHAR(30),
    monto_a_cobrar NUMERIC(12,2) DEFAULT 0,
    claimed_at TIMESTAMPTZ,
    picked_up_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_delivery_assignments_tenant ON delivery_assignments(tenant_id, estado);
CREATE INDEX IF NOT EXISTS idx_delivery_assignments_comanda ON delivery_assignments(comanda_id);

-- 3. Prep time on agente_config
ALTER TABLE agente_config ADD COLUMN IF NOT EXISTS tiempo_estimado_preparacion INT DEFAULT 30;
