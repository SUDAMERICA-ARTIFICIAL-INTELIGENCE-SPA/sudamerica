-- Migration: Create reservaciones table for restaurant table reservations
-- Run on Cloud SQL: psql -h 34.31.63.29 -U postgres -d sudamerica

CREATE TABLE IF NOT EXISTS reservaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    mesa_id UUID REFERENCES mesas(id) ON DELETE SET NULL,
    fecha_reserva DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    cantidad_personas INT NOT NULL CHECK (cantidad_personas > 0),
    nombre_cliente VARCHAR(255) NOT NULL,
    rut VARCHAR(20),
    email VARCHAR(255),
    telefono VARCHAR(50),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE', 'CONFIRMADA', 'CANCELADA', 'COMPLETADA', 'NO_SHOW')),
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policy (matches project pattern)
ALTER TABLE reservaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE reservaciones FORCE ROW LEVEL SECURITY;

CREATE POLICY reservaciones_tenant_isolation ON reservaciones
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- Index for availability queries (date + tenant + active)
CREATE INDEX IF NOT EXISTS idx_reservaciones_disponibilidad
    ON reservaciones (tenant_id, fecha_reserva, hora_inicio, hora_fin)
    WHERE activo = true AND estado NOT IN ('CANCELADA');
