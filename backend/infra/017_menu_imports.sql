-- ============================================================
-- Menu Imports: tracks PDF/CSV/image imports with versioning
-- Supports preview/confirm workflow and official PDF selection
-- ============================================================

CREATE TABLE menu_imports (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    version           INT NOT NULL DEFAULT 1,
    source_type       VARCHAR(20) NOT NULL
                      CHECK (source_type IN ('PDF','CSV','IMAGE','URL')),
    filename          VARCHAR(500),
    original_pdf_path TEXT,
    original_pdf_url  TEXT,
    file_size_bytes   INT,
    content_type      VARCHAR(100),
    items_extracted   INT NOT NULL DEFAULT 0,
    items_confirmed   INT NOT NULL DEFAULT 0,
    categories_created INT NOT NULL DEFAULT 0,
    preview_data      JSONB,
    status            VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','CONFIRMED','CANCELLED')),
    set_as_official   BOOLEAN NOT NULL DEFAULT FALSE,
    activo            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_menu_imports_tenant ON menu_imports(tenant_id);
CREATE INDEX idx_menu_imports_tenant_version ON menu_imports(tenant_id, version DESC);

-- RLS (matches canonical pattern from 002_rls_policies.sql)
ALTER TABLE menu_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_imports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON menu_imports;
CREATE POLICY tenant_isolation ON menu_imports
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
