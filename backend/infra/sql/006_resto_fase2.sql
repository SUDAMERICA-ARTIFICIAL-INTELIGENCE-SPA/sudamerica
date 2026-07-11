-- 006_resto_fase2.sql — Sudamérica AI Resto Fase 2: Fidelización + Venta fields
-- MUST be executed in Cloud SQL BEFORE deploying backend with these columns.

-- A. Venta: tipo_entrega + numero_mesa
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20);
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS numero_mesa INTEGER;

-- D. Lead fidelización columns
ALTER TABLE leads ADD COLUMN IF NOT EXISTS estado_cliente VARCHAR(20) DEFAULT 'NUEVO';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_pedidos INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_gastado NUMERIC(12,2) DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS plato_favorito VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ultima_visita DATE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS frecuencia_dias INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags VARCHAR(50)[];

-- Index for estado_cliente filtering
CREATE INDEX IF NOT EXISTS idx_leads_estado_cliente ON leads (tenant_id, estado_cliente) WHERE activo = true;
