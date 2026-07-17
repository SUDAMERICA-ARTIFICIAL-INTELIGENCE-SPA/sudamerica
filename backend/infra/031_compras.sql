-- 031_compras.sql — OLA B: dominio Compras/Proveedores (hecho fuente nuevo).
--
-- Cierra el grafo de coherencia de la demo:
--   orden_compra → recepcion (ENTRADA de stock, feed de inventario/movimientos)
--                → factura_proveedor (EGRESO de caja / CxP, feed de dinero/flujo-caja)
--
-- Core relacional: proveedores, ordenes_compra + oc_items, recepciones + recepcion_items,
-- facturas_proveedor. Upstream ligero (items en jsonb): requisiciones, cotizaciones.
-- Todas con RLS tenant_isolation (imita 008_sucursales.sql). Idempotente (IF NOT EXISTS).
-- down: DROP TABLE IF EXISTS cotizaciones, requisiciones, facturas_proveedor,
--       recepcion_items, recepciones, oc_items, ordenes_compra, proveedores CASCADE;

-- ── proveedores ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proveedores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    rut VARCHAR(20),
    contacto_nombre VARCHAR(255),
    email VARCHAR(255),
    telefono VARCHAR(50),
    direccion TEXT,
    categoria VARCHAR(80),                       -- tipo de insumo (skincare, maquillaje, packaging...)
    condicion_pago VARCHAR(40) DEFAULT 'CONTADO',-- CONTADO / 30 DIAS / 60 DIAS
    lead_time_dias INTEGER DEFAULT 7,
    rating NUMERIC(3, 2) DEFAULT 0,              -- 0..5 (evaluacion)
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, nombre)
);
ALTER TABLE proveedores ENABLE ROW LEVEL SECURITY;
ALTER TABLE proveedores FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON proveedores;
CREATE POLICY tenant_isolation ON proveedores FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_proveedores_tenant_activo ON proveedores(tenant_id, activo);

-- ── ordenes_compra ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ordenes_compra (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    proveedor_id UUID NOT NULL REFERENCES proveedores(id) ON DELETE CASCADE,
    sucursal_id UUID REFERENCES sucursales(id),
    numero VARCHAR(30) NOT NULL,                 -- OC-2026-000123
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR', -- BORRADOR/ENVIADA/CONFIRMADA/RECIBIDA_PARCIAL/RECIBIDA/CANCELADA
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_esperada DATE,
    moneda VARCHAR(3) NOT NULL DEFAULT 'CLP',
    neto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    iva NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);
ALTER TABLE ordenes_compra ENABLE ROW LEVEL SECURITY;
ALTER TABLE ordenes_compra FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON ordenes_compra;
CREATE POLICY tenant_isolation ON ordenes_compra FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_oc_tenant_estado ON ordenes_compra(tenant_id, estado);
CREATE INDEX IF NOT EXISTS idx_oc_proveedor ON ordenes_compra(proveedor_id);

-- ── oc_items (líneas de la orden) ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS oc_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orden_compra_id UUID NOT NULL REFERENCES ordenes_compra(id) ON DELETE CASCADE,
    producto_id UUID REFERENCES productos(id),   -- nullable: puede ser insumo libre
    descripcion VARCHAR(255) NOT NULL,
    cantidad NUMERIC(12, 2) NOT NULL DEFAULT 1,
    cantidad_recibida NUMERIC(12, 2) NOT NULL DEFAULT 0,
    costo_unitario NUMERIC(14, 2) NOT NULL DEFAULT 0,
    subtotal NUMERIC(14, 2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_oc_items_oc ON oc_items(orden_compra_id);
-- (sin RLS propia: se accede siempre vía JOIN a ordenes_compra, ya aislada por tenant)

-- ── recepciones (entrada de mercadería → ENTRADA de stock) ──────────────────
CREATE TABLE IF NOT EXISTS recepciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    orden_compra_id UUID NOT NULL REFERENCES ordenes_compra(id) ON DELETE CASCADE,
    sucursal_id UUID REFERENCES sucursales(id),
    numero VARCHAR(30) NOT NULL,                 -- REC-2026-000045
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'COMPLETA', -- PARCIAL/COMPLETA
    recibido_por VARCHAR(255),
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);
ALTER TABLE recepciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE recepciones FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON recepciones;
CREATE POLICY tenant_isolation ON recepciones FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_recepciones_tenant_fecha ON recepciones(tenant_id, fecha);
CREATE INDEX IF NOT EXISTS idx_recepciones_oc ON recepciones(orden_compra_id);

-- ── recepcion_items (líneas recibidas → kardex de entradas) ─────────────────
CREATE TABLE IF NOT EXISTS recepcion_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recepcion_id UUID NOT NULL REFERENCES recepciones(id) ON DELETE CASCADE,
    oc_item_id UUID REFERENCES oc_items(id),
    producto_id UUID REFERENCES productos(id),
    descripcion VARCHAR(255) NOT NULL,
    cantidad NUMERIC(12, 2) NOT NULL DEFAULT 0,
    costo_unitario NUMERIC(14, 2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_recepcion_items_rec ON recepcion_items(recepcion_id);
CREATE INDEX IF NOT EXISTS idx_recepcion_items_prod ON recepcion_items(producto_id);

-- ── facturas_proveedor (documento de compra → EGRESO / CxP) ─────────────────
CREATE TABLE IF NOT EXISTS facturas_proveedor (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    proveedor_id UUID NOT NULL REFERENCES proveedores(id) ON DELETE CASCADE,
    orden_compra_id UUID REFERENCES ordenes_compra(id),
    numero VARCHAR(30) NOT NULL,                 -- folio del proveedor
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE/PAGADA/VENCIDA/ANULADA
    neto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    iva NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    monto_pagado NUMERIC(14, 2) NOT NULL DEFAULT 0,
    metodo_pago VARCHAR(30),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, proveedor_id, numero)
);
ALTER TABLE facturas_proveedor ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturas_proveedor FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON facturas_proveedor;
CREATE POLICY tenant_isolation ON facturas_proveedor FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_facturas_prov_tenant_estado ON facturas_proveedor(tenant_id, estado);
CREATE INDEX IF NOT EXISTS idx_facturas_prov_venc ON facturas_proveedor(fecha_vencimiento);

-- ── requisiciones (solicitud interna; upstream, items en jsonb) ─────────────
CREATE TABLE IF NOT EXISTS requisiciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sucursal_id UUID REFERENCES sucursales(id),
    numero VARCHAR(30) NOT NULL,                 -- REQ-2026-000012
    solicitante VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE/APROBADA/RECHAZADA/CONVERTIDA
    prioridad VARCHAR(10) NOT NULL DEFAULT 'MEDIA',  -- BAJA/MEDIA/ALTA
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,     -- [{descripcion, cantidad, producto_id}]
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);
ALTER TABLE requisiciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE requisiciones FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON requisiciones;
CREATE POLICY tenant_isolation ON requisiciones FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_requisiciones_tenant_estado ON requisiciones(tenant_id, estado);

-- ── cotizaciones (RFQ por proveedor; upstream, items en jsonb) ──────────────
CREATE TABLE IF NOT EXISTS cotizaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    proveedor_id UUID NOT NULL REFERENCES proveedores(id) ON DELETE CASCADE,
    requisicion_id UUID REFERENCES requisiciones(id),
    numero VARCHAR(30) NOT NULL,                 -- COT-2026-000031
    estado VARCHAR(20) NOT NULL DEFAULT 'RECIBIDA', -- RECIBIDA/SELECCIONADA/RECHAZADA
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    validez_dias INTEGER NOT NULL DEFAULT 15,
    total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,     -- [{descripcion, cantidad, costo_unitario}]
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);
ALTER TABLE cotizaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE cotizaciones FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON cotizaciones;
CREATE POLICY tenant_isolation ON cotizaciones FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_cotizaciones_tenant_estado ON cotizaciones(tenant_id, estado);
