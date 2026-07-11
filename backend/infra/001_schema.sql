-- ============================================================
-- Sudamérica AI: canonical schema snapshot
-- Multi-tenant via tenant_id + PostgreSQL Row-Level Security
-- Last updated: 2026-03-15 (quality gate remediation)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. tenants (global root table)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    plan VARCHAR(10) NOT NULL DEFAULT 'FREE' CHECK (plan IN ('FREE', 'ESTANDAR', 'PLUS', 'PRO')),
    max_users INT NOT NULL DEFAULT 3,
    max_leads_mes INT NOT NULL DEFAULT 100,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    config JSONB DEFAULT '{}'::jsonb,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. usuarios
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    apellido VARCHAR(255) NOT NULL DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'ASESOR' CHECK (role IN ('SUPERADMIN', 'ADMIN', 'PERSONAL', 'ASESOR', 'VIEWER')),
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- 3. categorias
CREATE TABLE categorias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, nombre)
);

-- 4. productos
CREATE TABLE productos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    categoria_id UUID REFERENCES categorias(id) ON DELETE SET NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio NUMERIC(12, 2) NOT NULL CHECK (precio >= 0),
    sku VARCHAR(100),
    imagen_url TEXT,
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    disponible BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. leads
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefono VARCHAR(50),
    empresa VARCHAR(255),
    sector VARCHAR(100),
    canal VARCHAR(30) NOT NULL DEFAULT 'WHATSAPP' CHECK (canal IN ('WHATSAPP', 'INSTAGRAM', 'FACEBOOK', 'WEB', 'TELEFONO', 'EMAIL', 'REFERIDO')),
    estado VARCHAR(30) NOT NULL DEFAULT 'NUEVO' CHECK (estado IN ('NUEVO', 'CONTACTADO', 'EN_PROCESO', 'CONVERTIDO', 'DESCARTADO')),
    valor_estimado NUMERIC(12, 2) DEFAULT 0,
    notas TEXT,
    asignado_a UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    intencion VARCHAR(100),
    score INT DEFAULT 0 CHECK (score >= 0 AND score <= 100),
    -- Fidelización fields (gastronomy)
    estado_cliente VARCHAR(20) DEFAULT 'NUEVO' CHECK (estado_cliente IN ('NUEVO', 'OCASIONAL', 'FRECUENTE', 'VIP', 'INACTIVO')),
    total_pedidos INT NOT NULL DEFAULT 0,
    total_gastado NUMERIC(12, 2) NOT NULL DEFAULT 0,
    plato_favorito VARCHAR(255),
    ultima_visita DATE,
    frecuencia_dias INT,
    tags JSONB,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. ventas
CREATE TABLE ventas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    producto_id UUID REFERENCES productos(id) ON DELETE SET NULL,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12, 2) NOT NULL CHECK (precio_unitario >= 0),
    total NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
    notas TEXT,
    tipo_entrega VARCHAR(20) CHECK (tipo_entrega IN ('MESA', 'DELIVERY', 'RETIRO')),
    numero_mesa INT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. agente_config
CREATE TABLE agente_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE UNIQUE,
    system_prompt TEXT NOT NULL DEFAULT 'Eres un asistente de ventas inteligente para una empresa latinoamericana.',
    modelo VARCHAR(100) NOT NULL DEFAULT 'openai/gpt-4o-mini',
    temperatura NUMERIC(3, 2) NOT NULL DEFAULT 0.3 CHECK (temperatura >= 0 AND temperatura <= 2),
    max_tokens INT NOT NULL DEFAULT 4096,
    voz_id VARCHAR(100),
    voz_nombre VARCHAR(255),
    umbral_confianza NUMERIC(3, 2) NOT NULL DEFAULT 0.85,
    sub_agentes_activos JSONB DEFAULT '{"RAG": true, "COTIZADOR": true, "SEGUIMIENTO": true}'::jsonb,
    auto_respuesta_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
    outbound_proactivo BOOLEAN NOT NULL DEFAULT FALSE,
    outbound_horario_inicio VARCHAR(5),
    outbound_horario_fin VARCHAR(5),
    outbound_mensaje_template TEXT,
    instrucciones_disponibilidad TEXT,
    knowledge_max_chars INT NOT NULL DEFAULT 6000,
    session_timeout_minutes INT NOT NULL DEFAULT 30,
    nombre_agente VARCHAR(100),
    personalidad TEXT,
    menu_pdf_url TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. revision_humana
CREATE TABLE revision_humana (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    mensaje_original TEXT NOT NULL,
    respuesta_ia TEXT NOT NULL,
    confianza NUMERIC(5, 4) NOT NULL,
    accion VARCHAR(20) CHECK (accion IN ('APROBAR', 'EDITAR', 'RECHAZAR')),
    respuesta_editada TEXT,
    operador_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    procesado BOOLEAN NOT NULL DEFAULT FALSE,
    tiempo_revision_ms INT,
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    delivery_timestamp TIMESTAMPTZ,
    delivery_error TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. stripe_events (global webhook idempotency)
CREATE TABLE stripe_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. contacts
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, phone)
);

-- 11. sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id),
    lead_id UUID,
    channel VARCHAR(50) NOT NULL DEFAULT 'WEB',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED', 'HUMAN_HANDOFF')),
    summary TEXT,
    closed_at TIMESTAMPTZ,
    token_count INT NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. ai_conversations
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INT DEFAULT 0,
    modelo VARCHAR(100),
    canal VARCHAR(30),
    external_wa_id VARCHAR(255),
    media_url TEXT,
    media_type VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'SENT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. ai_embeddings
CREATE TABLE ai_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. smart_alerts
CREATE TABLE smart_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    mensaje TEXT NOT NULL,
    leido BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. sales_targets
CREATE TABLE sales_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asesor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    periodo VARCHAR(7) NOT NULL,
    meta_ventas NUMERIC(12, 2) NOT NULL DEFAULT 0,
    meta_leads INT NOT NULL DEFAULT 0,
    meta_conversion NUMERIC(5, 4) NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. evolution_instances
CREATE TABLE evolution_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    instance_name VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'DISCONNECTED',
    phone_number VARCHAR(50),
    evo_token VARCHAR(255)
);

-- 17. llm_provider_keys
CREATE TABLE llm_provider_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provider VARCHAR(50) NOT NULL,
    api_key TEXT NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    default_model VARCHAR(100) NOT NULL,
    label VARCHAR(255),
    CONSTRAINT uq_llm_key_tenant_provider UNIQUE (tenant_id, provider)
);

-- 18. tenant_knowledge
CREATE TABLE tenant_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    priority INT NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 19. task_logs
CREATE TABLE task_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL,
    destinatario VARCHAR(255) NOT NULL,
    contenido TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    error_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. mesas (restaurant tables)
CREATE TABLE mesas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    numero INT NOT NULL,
    nombre VARCHAR(100),
    capacidad INT NOT NULL DEFAULT 4,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, numero)
);

-- 21. modifier_groups (menu option groups)
CREATE TABLE modifier_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('SINGLE_SELECT', 'MULTI_SELECT')),
    obligatorio BOOLEAN NOT NULL DEFAULT FALSE,
    max_selecciones INT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. modifiers (individual options within a group)
CREATE TABLE modifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    grupo_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    precio_delta NUMERIC(10, 2) NOT NULL DEFAULT 0,
    orden INT NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. producto_modifier_groups (M:N association)
CREATE TABLE producto_modifier_groups (
    producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    modifier_group_id UUID NOT NULL REFERENCES modifier_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (producto_id, modifier_group_id)
);

-- 24. comandas (kitchen orders)
CREATE TABLE comandas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    venta_id UUID REFERENCES ventas(id) ON DELETE SET NULL,
    cliente_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    tipo_entrega VARCHAR(20) NOT NULL CHECK (tipo_entrega IN ('MESA', 'DELIVERY', 'RETIRO')),
    numero_mesa INT,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'EN_COCINA', 'LISTO', 'ENTREGADO', 'CANCELADO')),
    canal_origen VARCHAR(20) NOT NULL CHECK (canal_origen IN ('WHATSAPP', 'WEB', 'PRESENCIAL')),
    notas TEXT,
    prioridad INT NOT NULL DEFAULT 0,
    tiempo_estimado_min INT,
    entregado_at TIMESTAMPTZ,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 25. comanda_items (order line items)
CREATE TABLE comanda_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comanda_id UUID NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    producto_id UUID NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0),
    modifiers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal NUMERIC(10, 2) NOT NULL CHECK (subtotal >= 0),
    notas TEXT
);

-- 26. reservaciones (restaurant table reservations)
CREATE TABLE reservaciones (
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

-- 27. platform_config (global settings, no tenant scope)
CREATE TABLE platform_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

-- 27. api_key_audit (rotation log, no tenant scope)
CREATE TABLE api_key_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    performed_by UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    old_key_masked VARCHAR(20),
    new_key_masked VARCHAR(20),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Cross-tenant UNIQUE constraints (enable tenant-scoped FKs)
-- ============================================================

ALTER TABLE categorias
    ADD CONSTRAINT uq_categorias_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE usuarios
    ADD CONSTRAINT uq_usuarios_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE leads
    ADD CONSTRAINT uq_leads_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE productos
    ADD CONSTRAINT uq_productos_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE contacts
    ADD CONSTRAINT uq_contacts_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE sessions
    ADD CONSTRAINT uq_sessions_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE ventas
    ADD CONSTRAINT uq_ventas_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE modifier_groups
    ADD CONSTRAINT uq_modifier_groups_tenant_id_id UNIQUE (tenant_id, id);

ALTER TABLE comandas
    ADD CONSTRAINT uq_comandas_tenant_id_id UNIQUE (tenant_id, id);

-- ============================================================
-- Cross-tenant FOREIGN KEYS (enforce tenant isolation in JOINs)
-- ============================================================

ALTER TABLE productos
    ADD CONSTRAINT fk_productos_categoria_tenant
    FOREIGN KEY (tenant_id, categoria_id) REFERENCES categorias (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE leads
    ADD CONSTRAINT fk_leads_asignado_a_tenant
    FOREIGN KEY (tenant_id, asignado_a) REFERENCES usuarios (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ventas
    ADD CONSTRAINT fk_ventas_lead_tenant
    FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ventas
    ADD CONSTRAINT fk_ventas_producto_tenant
    FOREIGN KEY (tenant_id, producto_id) REFERENCES productos (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ventas
    ADD CONSTRAINT fk_ventas_usuario_tenant
    FOREIGN KEY (tenant_id, usuario_id) REFERENCES usuarios (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE revision_humana
    ADD CONSTRAINT fk_revision_humana_lead_tenant
    FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE revision_humana
    ADD CONSTRAINT fk_revision_humana_operador_tenant
    FOREIGN KEY (tenant_id, operador_id) REFERENCES usuarios (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE sessions
    ADD CONSTRAINT fk_sessions_contact_tenant
    FOREIGN KEY (tenant_id, contact_id) REFERENCES contacts (tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE sessions
    ADD CONSTRAINT fk_sessions_lead_tenant
    FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ai_conversations
    ADD CONSTRAINT fk_ai_conversations_usuario_tenant
    FOREIGN KEY (tenant_id, usuario_id) REFERENCES usuarios (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ai_conversations
    ADD CONSTRAINT fk_ai_conversations_lead_tenant
    FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE ai_conversations
    ADD CONSTRAINT fk_ai_conversations_session_tenant
    FOREIGN KEY (tenant_id, session_id) REFERENCES sessions (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE smart_alerts
    ADD CONSTRAINT fk_smart_alerts_lead_tenant
    FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE sales_targets
    ADD CONSTRAINT fk_sales_targets_asesor_tenant
    FOREIGN KEY (tenant_id, asesor_id) REFERENCES usuarios (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE modifiers
    ADD CONSTRAINT fk_modifiers_grupo_tenant
    FOREIGN KEY (tenant_id, grupo_id) REFERENCES modifier_groups (tenant_id, id) ON DELETE CASCADE;

ALTER TABLE comandas
    ADD CONSTRAINT fk_comandas_venta_tenant
    FOREIGN KEY (tenant_id, venta_id) REFERENCES ventas (tenant_id, id) ON DELETE SET NULL;

ALTER TABLE comandas
    ADD CONSTRAINT fk_comandas_cliente_tenant
    FOREIGN KEY (tenant_id, cliente_id) REFERENCES leads (tenant_id, id) ON DELETE SET NULL;
