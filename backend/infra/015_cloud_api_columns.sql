-- 015: Add Cloud API columns to evolution_instances
-- Required for WhatsApp Business Cloud API (Meta oficial) support

ALTER TABLE evolution_instances
    ADD COLUMN IF NOT EXISTS integration VARCHAR(30) NOT NULL DEFAULT 'WHATSAPP-BAILEYS',
    ADD COLUMN IF NOT EXISTS meta_business_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS meta_number_id VARCHAR(100);

COMMENT ON COLUMN evolution_instances.integration IS 'WHATSAPP-BAILEYS (QR scan) or WHATSAPP-BUSINESS (Cloud API oficial)';
COMMENT ON COLUMN evolution_instances.meta_business_id IS 'WhatsApp Business Account ID from Meta Business Manager';
COMMENT ON COLUMN evolution_instances.meta_number_id IS 'WhatsApp Number ID from Facebook Developers app';
