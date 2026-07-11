-- 024: F5 multi-rubro — recurso reservable genérico (fase EXPAND, sin rename)
-- mesas.tipo tipifica el recurso físico ('mesa', 'silla', 'box', ...). El contract
-- (rename mesas→recursos y reservaciones.mesa_id→recurso_id con doble escritura)
-- queda diferido a después del piloto; esta fase es aditiva y backwards-compatible.
-- RLS: tabla mesas ya cubierta por tenant_isolation (002_rls_policies.sql).
-- down: ALTER TABLE mesas DROP COLUMN IF EXISTS tipo;

ALTER TABLE mesas
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(30) NOT NULL DEFAULT 'mesa';

COMMENT ON COLUMN mesas.tipo IS 'Tipo de recurso fisico reservable (mesa/silla/box...), F5 multi-rubro';
