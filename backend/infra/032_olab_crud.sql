-- 032_olab_crud.sql — OLA B: tablas de dominios chicos (B3).
--   devoluciones (RMA), mensaje_plantillas, documentos_archivos, campanas.
-- Todas con RLS tenant_isolation. Idempotente (IF NOT EXISTS).
-- down: DROP TABLE IF EXISTS campanas, documentos_archivos, mensaje_plantillas, devoluciones CASCADE;

-- ── devoluciones (RMA sobre una venta/pedido) ───────────────────────────────
CREATE TABLE IF NOT EXISTS devoluciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id),
    venta_id UUID REFERENCES ventas(id),
    sucursal_id UUID REFERENCES sucursales(id),
    numero VARCHAR(30) NOT NULL,                 -- DEV-2026-000007
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    motivo VARCHAR(60) NOT NULL DEFAULT 'OTRO',  -- DEFECTO/TALLA/INSATISFACCION/ERROR_ENVIO/OTRO
    estado VARCHAR(20) NOT NULL DEFAULT 'SOLICITADA', -- SOLICITADA/APROBADA/RECHAZADA/REEMBOLSADA
    metodo_reembolso VARCHAR(30),                -- GIFTCARD/EFECTIVO/TARJETA/CAMBIO
    monto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,     -- [{producto, cantidad, monto}]
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);
ALTER TABLE devoluciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE devoluciones FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON devoluciones;
CREATE POLICY tenant_isolation ON devoluciones FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_devoluciones_tenant_estado ON devoluciones(tenant_id, estado);

-- ── mensaje_plantillas (plantillas de conversación) ─────────────────────────
CREATE TABLE IF NOT EXISTS mensaje_plantillas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(120) NOT NULL,
    canal VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP', -- WHATSAPP/INSTAGRAM/EMAIL/SMS
    categoria VARCHAR(40) DEFAULT 'GENERAL',       -- BIENVENIDA/POSTVENTA/PROMO/COBRANZA/GENERAL
    contenido TEXT NOT NULL,
    variables JSONB NOT NULL DEFAULT '[]'::jsonb,  -- ["nombre","total"]
    usos INTEGER NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, nombre)
);
ALTER TABLE mensaje_plantillas ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensaje_plantillas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON mensaje_plantillas;
CREATE POLICY tenant_isolation ON mensaje_plantillas FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_plantillas_tenant ON mensaje_plantillas(tenant_id, activo);

-- ── documentos_archivos (biblioteca de documentos) ──────────────────────────
CREATE TABLE IF NOT EXISTS documentos_archivos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'OTRO',    -- BOLETA/FACTURA/CONTRATO/IMAGEN/PLANILLA/OTRO
    categoria VARCHAR(60),
    url TEXT,
    mime VARCHAR(120),
    tamano_kb INTEGER DEFAULT 0,
    subido_por VARCHAR(255),
    entidad_tipo VARCHAR(40),                    -- proveedor/cliente/producto/... (opcional)
    entidad_id UUID,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE documentos_archivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos_archivos FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON documentos_archivos;
CREATE POLICY tenant_isolation ON documentos_archivos FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_documentos_tenant_tipo ON documentos_archivos(tenant_id, tipo);

-- ── campanas (marketing; capacidad `campanas`) ──────────────────────────────
CREATE TABLE IF NOT EXISTS campanas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(160) NOT NULL,
    canal VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP', -- WHATSAPP/INSTAGRAM/EMAIL/SMS
    tipo VARCHAR(30) NOT NULL DEFAULT 'PROMO',     -- PROMO/FIDELIZACION/LANZAMIENTO/REACTIVACION
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',-- BORRADOR/PROGRAMADA/ACTIVA/FINALIZADA
    segmento VARCHAR(60),                          -- VIP/FRECUENTE/INACTIVO/TODOS
    fecha_inicio DATE,
    fecha_fin DATE,
    presupuesto NUMERIC(14, 2) NOT NULL DEFAULT 0,
    enviados INTEGER NOT NULL DEFAULT 0,
    abiertos INTEGER NOT NULL DEFAULT 0,
    conversiones INTEGER NOT NULL DEFAULT 0,
    ingresos_generados NUMERIC(14, 2) NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, nombre)
);
ALTER TABLE campanas ENABLE ROW LEVEL SECURITY;
ALTER TABLE campanas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON campanas;
CREATE POLICY tenant_isolation ON campanas FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
CREATE INDEX IF NOT EXISTS idx_campanas_tenant_estado ON campanas(tenant_id, estado);
