-- Add recordatorio_enviado column to reservaciones table
-- Prevents double-sending of WhatsApp reminders
ALTER TABLE reservaciones
  ADD COLUMN IF NOT EXISTS recordatorio_enviado BOOLEAN NOT NULL DEFAULT false;
