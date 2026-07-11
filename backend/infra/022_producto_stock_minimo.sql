-- 022: F3 multi-rubro — umbral de stock mínimo por producto (módulo inventario)
-- Aditiva y backwards-compatible: default 0 = sin umbral (solo alerta al agotarse).
-- RLS: la tabla productos ya está cubierta por tenant_isolation (002_rls_policies.sql);
-- una columna nueva no requiere política adicional.
-- down: ALTER TABLE productos DROP COLUMN IF EXISTS stock_minimo;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS stock_minimo INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN productos.stock_minimo IS 'Umbral de alerta stock_bajo (modulo inventario, F3 multi-rubro); 0 = solo alerta al agotarse';
