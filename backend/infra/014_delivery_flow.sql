-- 014_delivery_flow.sql — Delivery flow: cost per branch, address, payment, driver group
-- Run manually in Cloud SQL

-- 1. Sucursal delivery config
ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS costo_delivery NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS grupo_repartidores_jid VARCHAR(60);

-- 2. Comanda delivery fields
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS direccion_entrega TEXT;
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS ubicacion_lat NUMERIC(10, 7);
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS ubicacion_lng NUMERIC(10, 7);
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(30);
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS costo_delivery NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS pago_confirmado BOOLEAN DEFAULT FALSE;
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS repartidor_nombre VARCHAR(100);
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS repartidor_phone VARCHAR(20);
