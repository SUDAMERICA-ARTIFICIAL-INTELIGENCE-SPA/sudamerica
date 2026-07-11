-- ============================================================
-- Migration: Schema catch-up for Cloud SQL prod (2026-03-15)
-- Quality gate remediation — brings prod DB in sync with
-- 001_schema.sql canonical snapshot.
--
-- INSTRUCTIONS:
--   1. Run against Cloud SQL prod during low-traffic window
--   2. Execute each section in order (tables first, then columns,
--      then constraints, then indexes)
--   3. IF NOT EXISTS / ADD COLUMN IF NOT EXISTS are used for
--      idempotency — safe to re-run
-- ============================================================

BEGIN;

-- ============================================================
-- A. New tables
-- ============================================================

-- 20. mesas
CREATE TABLE IF NOT EXISTS mesas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    numero INT NOT NULL,
    nombre VARCHAR(100),
    capacidad INT NOT NULL DEFAULT 4,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);

-- 21. modifier_groups
CREATE TABLE IF NOT EXISTS modifier_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('SINGLE_SELECT', 'MULTI_SELECT')),
    obligatorio BOOLEAN NOT NULL DEFAULT FALSE,
    max_selecciones INT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. modifiers
CREATE TABLE IF NOT EXISTS modifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    grupo_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    precio_delta NUMERIC(10, 2) NOT NULL DEFAULT 0,
    orden INT NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. producto_modifier_groups
CREATE TABLE IF NOT EXISTS producto_modifier_groups (
    producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    modifier_group_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (producto_id, modifier_group_id)
);

-- 24. comandas
CREATE TABLE IF NOT EXISTS comandas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    venta_id UUID REFERENCES ventas(id) ON DELETE SET NULL,
    cliente_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    tipo_entrega VARCHAR(20) NOT NULL CHECK (tipo_entrega IN ('MESA', 'DELIVERY', 'RETIRO')),
    numero_mesa INT,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'EN_COCINA', 'LISTO', 'ENTREGADO', 'CANCELADO')),
    canal_origen VARCHAR(20) NOT NULL CHECK (canal_origen IN ('WHATSAPP', 'WEB', 'PRESENCIAL')),
    notas TEXT,
    prioridad INT NOT NULL DEFAULT 0,
    tiempo_estimado_min INT,
    entregado_at TIMESTAMPTZ,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 25. comanda_items
CREATE TABLE IF NOT EXISTS comanda_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comanda_id UUID NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    producto_id UUID NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0),
    modifiers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal NUMERIC(10, 2) NOT NULL CHECK (subtotal >= 0),
    notas TEXT
);

-- 26. platform_config
CREATE TABLE IF NOT EXISTS platform_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

-- 27. api_key_audit
CREATE TABLE IF NOT EXISTS api_key_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    performed_by UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    old_key_masked VARCHAR(20),
    new_key_masked VARCHAR(20),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- B. New columns on existing tables
-- ============================================================

-- leads: fidelización fields
ALTER TABLE leads ADD COLUMN IF NOT EXISTS estado_cliente VARCHAR(20) DEFAULT 'NUEVO';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_pedidos INT NOT NULL DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_gastado NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS plato_favorito VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ultima_visita DATE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS frecuencia_dias INT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags JSONB;

-- leads: add CHECK constraint for estado_cliente
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'leads_estado_cliente_check'
  ) THEN
    ALTER TABLE leads ADD CONSTRAINT leads_estado_cliente_check
      CHECK (estado_cliente IN ('NUEVO', 'OCASIONAL', 'FRECUENTE', 'VIP', 'INACTIVO'));
  END IF;
END $$;

-- productos: disponible toggle
ALTER TABLE productos ADD COLUMN IF NOT EXISTS disponible BOOLEAN NOT NULL DEFAULT TRUE;

-- ventas: delivery fields
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20);
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS numero_mesa INT;

-- ventas: add CHECK constraint for tipo_entrega
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ventas_tipo_entrega_check'
  ) THEN
    ALTER TABLE ventas ADD CONSTRAINT ventas_tipo_entrega_check
      CHECK (tipo_entrega IN ('MESA', 'DELIVERY', 'RETIRO'));
  END IF;
END $$;

-- agente_config: new agent identity + availability fields
ALTER TABLE agente_config ADD COLUMN IF NOT EXISTS instrucciones_disponibilidad TEXT;
ALTER TABLE agente_config ADD COLUMN IF NOT EXISTS nombre_agente VARCHAR(100);
ALTER TABLE agente_config ADD COLUMN IF NOT EXISTS personalidad TEXT;
ALTER TABLE agente_config ADD COLUMN IF NOT EXISTS menu_pdf_url TEXT;

-- tenants.plan: expand CHECK to include ESTANDAR and PLUS
-- Drop old CHECK, add new one
DO $$
BEGIN
  -- Drop old constraint if exists
  ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_check;
  -- Add expanded constraint
  ALTER TABLE tenants ADD CONSTRAINT tenants_plan_check
    CHECK (plan IN ('FREE', 'ESTANDAR', 'PLUS', 'PRO'));
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'tenants_plan_check update skipped: %', SQLERRM;
END $$;

-- usuarios.role: expand CHECK to include SUPERADMIN and PERSONAL
DO $$
BEGIN
  ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_role_check;
  ALTER TABLE usuarios ADD CONSTRAINT usuarios_role_check
    CHECK (role IN ('SUPERADMIN', 'ADMIN', 'PERSONAL', 'ASESOR', 'VIEWER'));
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'usuarios_role_check update skipped: %', SQLERRM;
END $$;

-- ============================================================
-- C. Fix convention violations
-- ============================================================

-- sales_targets: DOUBLE PRECISION → NUMERIC (Gate D convention)
-- Only alter if column type is double precision
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sales_targets' AND column_name = 'meta_ventas'
      AND data_type = 'double precision'
  ) THEN
    ALTER TABLE sales_targets
      ALTER COLUMN meta_ventas TYPE NUMERIC(12, 2) USING meta_ventas::NUMERIC(12, 2);
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sales_targets' AND column_name = 'meta_conversion'
      AND data_type = 'double precision'
  ) THEN
    ALTER TABLE sales_targets
      ALTER COLUMN meta_conversion TYPE NUMERIC(5, 4) USING meta_conversion::NUMERIC(5, 4);
  END IF;
END $$;

-- ============================================================
-- D. Cross-tenant UNIQUE constraints for new tables
-- ============================================================

ALTER TABLE ventas
  ADD CONSTRAINT uq_ventas_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE modifier_groups
  ADD CONSTRAINT uq_modifier_groups_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE comandas
  ADD CONSTRAINT uq_comandas_tenant_id_id UNIQUE (tenant_id, id);

-- ============================================================
-- E. Cross-tenant FOREIGN KEYS for new tables
-- ============================================================

ALTER TABLE modifiers
  ADD CONSTRAINT fk_modifiers_grupo_tenant
  FOREIGN KEY (tenant_id, grupo_id) REFERENCES modifier_groups (tenant_id, id) ON DELETE CASCADE;

ALTER TABLE comandas
  ADD CONSTRAINT fk_comandas_venta_tenant
  FOREIGN KEY (tenant_id, venta_id) REFERENCES ventas (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE comandas
  ADD CONSTRAINT fk_comandas_cliente_tenant
  FOREIGN KEY (tenant_id, cliente_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

-- ============================================================
-- F. RLS for new tables
-- ============================================================

ALTER TABLE mesas ENABLE ROW LEVEL SECURITY;
ALTER TABLE mesas FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON mesas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE modifier_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifier_groups FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON modifier_groups
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE modifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE modifiers FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON modifiers
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

ALTER TABLE comandas ENABLE ROW LEVEL SECURITY;
ALTER TABLE comandas FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON comandas
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- ============================================================
-- G. Base indexes for new tables
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_mesas_tenant_activo
  ON mesas(tenant_id, activo);

CREATE INDEX IF NOT EXISTS idx_modifier_groups_tenant_activo
  ON modifier_groups(tenant_id, activo);

CREATE INDEX IF NOT EXISTS idx_modifiers_tenant_activo
  ON modifiers(tenant_id, activo);

CREATE INDEX IF NOT EXISTS idx_modifiers_grupo
  ON modifiers(grupo_id);

CREATE INDEX IF NOT EXISTS idx_pmg_producto
  ON producto_modifier_groups(producto_id);

CREATE INDEX IF NOT EXISTS idx_pmg_modifier_group
  ON producto_modifier_groups(modifier_group_id);

CREATE INDEX IF NOT EXISTS idx_comandas_tenant_estado
  ON comandas(tenant_id, estado);

CREATE INDEX IF NOT EXISTS idx_comandas_tenant_created
  ON comandas(tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comandas_tenant_cliente
  ON comandas(tenant_id, cliente_id);

CREATE INDEX IF NOT EXISTS idx_comandas_tenant_venta
  ON comandas(tenant_id, venta_id);

CREATE INDEX IF NOT EXISTS idx_comanda_items_comanda
  ON comanda_items(comanda_id);

CREATE INDEX IF NOT EXISTS idx_comanda_items_producto
  ON comanda_items(producto_id);

CREATE INDEX IF NOT EXISTS idx_api_key_audit_created
  ON api_key_audit(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_key_audit_provider
  ON api_key_audit(provider);

COMMIT;

-- ============================================================
-- H. Quality gate remediation indexes (CONCURRENTLY — run
--    OUTSIDE transaction block, one at a time)
-- ============================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revision_humana_operador
  ON revision_humana(tenant_id, operador_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_conv_usuario
  ON ai_conversations(tenant_id, usuario_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smart_alerts_lead
  ON smart_alerts(tenant_id, lead_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_lead
  ON sessions(tenant_id, lead_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_plan_activo
  ON tenants(plan, activo);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evolution_instances_status
  ON evolution_instances(status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evolution_instances_created
  ON evolution_instances(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_llm_provider_keys_created
  ON llm_provider_keys(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_estado_cliente
  ON leads(tenant_id, estado_cliente);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_ultima_visita
  ON leads(tenant_id, ultima_visita DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productos_disponible
  ON productos(tenant_id, disponible) WHERE disponible = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_conv_external_wa
  ON ai_conversations(external_wa_id) WHERE external_wa_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ventas_tipo_entrega
  ON ventas(tenant_id, tipo_entrega);
