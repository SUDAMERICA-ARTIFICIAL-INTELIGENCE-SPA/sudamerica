-- 021_schema_reconcile.sql
-- Bring databases created from the historical snapshot up to the current ORM shape.

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS costo NUMERIC(12, 2);

ALTER TABLE comanda_items
    ADD COLUMN IF NOT EXISTS costo_unitario NUMERIC(10, 2);
