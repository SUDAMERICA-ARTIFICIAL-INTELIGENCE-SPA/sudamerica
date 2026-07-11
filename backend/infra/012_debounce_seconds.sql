-- 012: Add debounce_seconds to agente_config
-- Controls how long to wait for consecutive messages before AI responds

ALTER TABLE agente_config
    ADD COLUMN IF NOT EXISTS debounce_seconds NUMERIC(4,1) NOT NULL DEFAULT 4.0;

COMMENT ON COLUMN agente_config.debounce_seconds IS
    'Seconds to buffer consecutive messages before AI responds (0 = disabled)';
