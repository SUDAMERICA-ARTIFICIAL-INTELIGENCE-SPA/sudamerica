-- 023: F4 multi-rubro — estado de orden genérico EN_PROCESO (rubros sin cocina)
-- Expand del CHECK de comandas.estado (patrón expand-then-contract). Restaurante
-- nunca emite EN_PROCESO (su FSM no lo alcanza) → backwards-compatible.
-- RLS: sin cambios (constraint de dominio, no de acceso).
-- down (solo si no quedan filas con estado = 'EN_PROCESO'):
--   ALTER TABLE comandas DROP CONSTRAINT comandas_estado_check;
--   ALTER TABLE comandas ADD CONSTRAINT comandas_estado_check
--       CHECK (estado IN ('PENDIENTE', 'EN_COCINA', 'LISTO', 'ENTREGADO', 'CANCELADO'));

ALTER TABLE comandas DROP CONSTRAINT IF EXISTS comandas_estado_check;
ALTER TABLE comandas ADD CONSTRAINT comandas_estado_check
    CHECK (estado IN ('PENDIENTE', 'EN_COCINA', 'EN_PROCESO', 'LISTO', 'ENTREGADO', 'CANCELADO'));
