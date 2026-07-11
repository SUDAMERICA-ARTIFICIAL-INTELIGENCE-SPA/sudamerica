-- ============================================================
-- Password reset tokens (self-service password recovery)
-- Run manually in Cloud SQL before deploying the updated code.
-- ============================================================

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token VARCHAR(128) NOT NULL UNIQUE,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token) WHERE used = FALSE;
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);

-- Add email_verification_token to usuarios (nullable, one-time use)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(128);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email_verification_expires TIMESTAMPTZ;
