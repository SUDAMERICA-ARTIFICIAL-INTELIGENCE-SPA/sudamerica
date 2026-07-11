-- Migration: Add media_url and media_type columns to ai_conversations
-- Required for WhatsApp media support (images, PDFs, audio, video)
-- Run on Cloud SQL prod: psql -h 34.31.63.29 -U postgres -d sudamerica

ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS media_url TEXT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS media_type VARCHAR(20);
