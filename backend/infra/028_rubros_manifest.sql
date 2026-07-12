-- 028_rubros_manifest.sql
-- Fase B (Paso 5): persiste el manifiesto de rubro en una tabla BD global + versión + anclaje.
--
-- Contexto: hasta el Paso 4 el manifiesto vivía SOLO en codigo
-- (`backend/shared/rubros/diccionario.py`), no editable en runtime y sin noción de version.
-- Esta migracion crea la tabla global `rubros` (proyeccion seedeada de `diccionario.py` via el
-- fixture `frontend/lib/__fixtures__/rubros.manifest.json`), añade el contador global de version
-- del manifiesto en `platform_config`, y añade la columna de anclaje de version a `sessions` y
-- `ai_conversations`. El seed de datos (filas de `rubros` + init del contador) vive en la
-- migracion 029, generada de forma reproducible por `tools/gen_rubros_seed.mjs` desde el fixture.
--
-- Seguridad / RLS: `rubros` es una tabla de REFERENCIA GLOBAL (sin `tenant_id`), igual que
-- `platform_config` y `api_key_audit`. Por eso NO lleva `tenant_isolation` ni RLS: no hay
-- superficie cross-tenant que aislar (no contiene datos de ningun tenant). La ESCRITURA se
-- restringe en la capa de aplicacion al admin de plataforma (SuperAdminOnly), igual que
-- `platform_config`. La LECTURA es global (vocabulario de rubro, no dato sensible).
--
-- Idempotente (IF NOT EXISTS). Columnas espejo del contrato `RubroManifest`
-- (`api_execute/app/schemas/tenant_config.py`, Paso 4).
-- down:
--   DROP TABLE IF EXISTS rubros;
--   ALTER TABLE sessions DROP COLUMN IF EXISTS manifest_version;
--   ALTER TABLE ai_conversations DROP COLUMN IF EXISTS manifest_version;
--   DELETE FROM platform_config WHERE key = 'rubro_manifest_version';

-- Tabla global de manifiestos de rubro (proyeccion seedeada de diccionario.py).
CREATE TABLE IF NOT EXISTS rubros (
    key                 VARCHAR(80) PRIMARY KEY,
    nombre              TEXT        NOT NULL,
    emoji               TEXT        NOT NULL,
    sector              TEXT        NOT NULL,
    labels              JSONB       NOT NULL,               -- 12 primitivas -> label visible
    capacidades         JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- lista, orden CAP_ORDER
    sub_entidad_label   TEXT        NULL,
    recurso             BOOLEAN     NOT NULL DEFAULT FALSE,
    variantes           BOOLEAN     NOT NULL DEFAULT TRUE,
    precio_medida       BOOLEAN     NOT NULL DEFAULT FALSE,
    categorias_semilla  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    version             INT         NOT NULL DEFAULT 1,     -- version por-fila (bump por edicion)
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          UUID        NULL REFERENCES usuarios(id) ON DELETE SET NULL
);

COMMENT ON TABLE rubros IS
    'Manifiesto de rubro persistido (Fase B, Paso 5). Tabla global de referencia (sin tenant_id, sin RLS); proyeccion seedeada de shared/rubros/diccionario.py via el fixture. Escritura solo admin de plataforma.';

-- Ancla de version del manifiesto por conversacion. NULL => no anclada => se resuelve a la
-- version vigente (loggeado). El flujo de chat vivo persiste por turno en ai_conversations
-- (session_id nullable); sessions.manifest_version queda por contrato para flujos basados en
-- sesion, con prioridad sobre el ancla por-primer-turno cuando exista.
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS manifest_version INT NULL;
COMMENT ON COLUMN sessions.manifest_version IS
    'Version del manifiesto de rubro anclada al crear la sesion (Fase B, Paso 5).';

ALTER TABLE ai_conversations
    ADD COLUMN IF NOT EXISTS manifest_version INT NULL;
COMMENT ON COLUMN ai_conversations.manifest_version IS
    'Version del manifiesto anclada a la conversacion (portador runtime del anclaje por primer turno, Fase B, Paso 5).';

-- El contador global `rubro_manifest_version` (fila en platform_config) se inicializa en la
-- migracion de seed 029 junto con las filas de rubros, para mantener 028 como esquema puro.
