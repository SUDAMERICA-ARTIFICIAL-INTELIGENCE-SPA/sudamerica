-- 030_rubros_lifecycle.sql
-- Fase C (Paso 6): el roster de rubros pasa de EDITABLE a EXTENSIBLE en runtime.
--
-- Contexto: hasta el Paso 5 la tabla global `rubros` (migracion 028, seed 029) era una
-- proyeccion byte-identica de `shared/rubros/diccionario.py`: un roster INVARIANTE que solo se
-- podia editar (PATCH), nunca crear/retirar. Esta migracion introduce por primera vez la nocion
-- de DOS CLASES de rubro y un ciclo de vida:
--   * origen='seed'    -> proyeccion de diccionario.py (verdad de codigo, test-guarded, membresia
--                         inmutable; restaurante byte-identico). Es lo que seedea 029.
--   * origen='runtime' -> rubro creado por un admin de plataforma via `POST /admin/rubros`, que
--                         vive SOLO en BD (no esta en diccionario.py ni en el fixture) y por tanto
--                         esta EXENTO de la cadena "una sola verdad" (diccionario=>fixture=>seed).
-- Y una bandera `activo` que da ciclo de vida (activar/desactivar) EXCLUSIVAMENTE a los rubros
-- runtime (un seed nunca se desactiva; ver app-layer en admin_service.set_rubro_activo).
--
-- Backfill implicito: las filas ya seedeadas por 029 (y cualquier re-seed idempotente) quedan
-- origen='seed', activo=true por DEFAULT. Esta migracion NO toca el CONTENIDO del seed: el
-- INSERT ... ON CONFLICT DO UPDATE de 029 no menciona `origen`/`activo`, asi que re-seedear
-- preserva ambas columnas y el rubro `restaurante` sigue byte-identico a `diccionario.py`.
--
-- INMUTABILIDAD de `origen`: una vez creada la fila, su `origen` no cambia (un seed no pasa a
-- runtime ni viceversa). No se aplica por trigger (evita acoplar la migracion a PL/pgSQL); el
-- CRUD admin nunca expone `origen` como campo editable (fail-closed en la capa de app).
--
-- Seguridad / RLS: `rubros` sigue siendo tabla de REFERENCIA GLOBAL (sin `tenant_id`, sin RLS);
-- la ESCRITURA (crear, editar, activar/desactivar) es solo admin de plataforma (SuperAdminOnly),
-- igual que en el Paso 5. Esta migracion NO agrega superficie cross-tenant.
--
-- Idempotente (ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS). Entra en la cadena
-- infra/[0-9]*.sql justo despues de 029.
-- down:
--   DROP INDEX IF EXISTS ix_rubros_activo;
--   ALTER TABLE rubros DROP COLUMN IF EXISTS activo;
--   ALTER TABLE rubros DROP COLUMN IF EXISTS origen;

-- Clase del rubro: 'seed' (proyeccion de codigo, membresia inmutable) | 'runtime' (creado por
-- admin, vive solo en BD). DEFAULT 'seed' => las filas seedeadas por 029 quedan clasificadas
-- como codigo sin tocar el seed.
ALTER TABLE rubros
    ADD COLUMN IF NOT EXISTS origen VARCHAR(10) NOT NULL DEFAULT 'seed'
        CHECK (origen IN ('seed', 'runtime'));
COMMENT ON COLUMN rubros.origen IS
    'Clase del rubro (Fase C, Paso 6): seed = proyeccion de diccionario.py (membresia inmutable, byte-identica); runtime = creado por admin, vive solo en BD (exento de la cadena una-sola-verdad). Inmutable tras crear.';

-- Ciclo de vida: solo los rubros runtime pueden desactivarse/reactivarse (app-layer). Un seed y
-- RUBRO_DEFAULT nunca se desactivan. DEFAULT true => el roster seedeado queda 100% activo.
ALTER TABLE rubros
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;
COMMENT ON COLUMN rubros.activo IS
    'Bandera de ciclo de vida (Fase C, Paso 6). Solo rubros origen=runtime pueden pasar a false (desactivar); los seed y RUBRO_DEFAULT permanecen true. El registro en proceso solo carga filas activas.';

-- Indice parcial: el registro carga en cada refresh() solo las filas activas (union seed+runtime).
CREATE INDEX IF NOT EXISTS ix_rubros_activo ON rubros (activo) WHERE activo;
