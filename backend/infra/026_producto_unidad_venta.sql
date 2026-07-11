-- 026: F6 multi-rubro — precio por medida/peso (fase expand)
-- productos.unidad_venta declara la unidad del precio ('unidad', 'kg', 'm2', 'hora'…).
-- Aditiva y backwards-compatible (default 'unidad' = comportamiento actual). La lógica
-- de cálculo por peso en el flujo de venta llega con el primer rubro que lo use.
-- down: ALTER TABLE productos DROP COLUMN IF EXISTS unidad_venta;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS unidad_venta VARCHAR(20) NOT NULL DEFAULT 'unidad';

COMMENT ON COLUMN productos.unidad_venta IS 'Unidad del precio (unidad/kg/m2/hora...), modulo precio_medida F6';
