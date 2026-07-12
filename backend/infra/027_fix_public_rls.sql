-- 027_fix_public_rls.sql
-- Cierra la lectura pública cross-tenant de `mesas` (Fase A, Paso 4 · invariante RLS #1).
--
-- 013_mesa_qr.sql creó `qr_token_public_lookup ON mesas USING (qr_token IS NOT NULL)`.
-- Como `qr_token` es NOT NULL en TODAS las filas de `mesas`, ese predicado es siempre
-- verdadero: al combinarse (policy permissive → OR) con `tenant_isolation`, cualquier
-- SELECT sobre `mesas` podía leer filas de OTROS tenants, rompiendo el aislamiento RLS.
--
-- Esta migración restringe la policy al contexto del escaneo QR público: el endpoint
-- `/api/v1/public/mesas/qr/{token}` fija `app.allow_qr_lookup='true'` (via
-- `set_qr_lookup_context`) ANTES del SELECT filtrado por token exacto, por lo que el
-- escaneo público sigue funcionando; fuera de ese contexto (peticiones normales de
-- tenant, donde el flag no está) solo aplica `tenant_isolation` → sin fuga cross-tenant.
--
-- Idempotente (DROP POLICY IF EXISTS). NO edita la migración histórica 013 ya aplicada;
-- la re-aplicación de esta policy la supera. Consistente con `public_read_for_joins`
-- (sucursales) y `evolution_instances_read`, ya gateadas por su GUC respectivo.

ALTER TABLE mesas ENABLE ROW LEVEL SECURITY;
ALTER TABLE mesas FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS qr_token_public_lookup ON mesas;
CREATE POLICY qr_token_public_lookup ON mesas
    FOR SELECT
    USING (
        current_setting('app.allow_qr_lookup', true) = 'true'
        AND qr_token IS NOT NULL
    );
