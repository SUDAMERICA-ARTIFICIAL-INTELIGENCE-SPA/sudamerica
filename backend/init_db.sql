\set ON_ERROR_STOP on

-- Sudamérica AI MVP -- fresh database bootstrap
-- Use this file only on an empty database.
-- For existing databases, run Alembic:
--   python run_alembic.py upgrade head

\ir infra/001_schema.sql
\ir infra/002_rls_policies.sql
\ir infra/003_indexes.sql

-- ============================================================
-- Seed data
-- ============================================================

INSERT INTO tenants (id, nombre, slug, plan, max_users, max_leads_mes)
VALUES (
    'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd',
    'SiAvanza Demo',
    'siavanza-demo',
    'PRO',
    15,
    99999
);

INSERT INTO usuarios (id, tenant_id, nombre, apellido, email, hashed_password, role)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd',
    'Benjamin',
    'Abarca',
    'admin@siavanza.cl',
    '$2b$12$LJ3m4ys1qGk8vGOe2g5Kyu3jEz5WX5z0GhVhvF.RHYZ5GqN5qPfDm',
    'ADMIN'
);

-- Categorias = secciones del menu gastronomico
INSERT INTO categorias (id, tenant_id, nombre) VALUES
    ('11111111-1111-1111-1111-111111111111', 'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Entradas'),
    ('22222222-2222-2222-2222-222222222222', 'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Platos de Fondo'),
    ('33333333-3333-3333-3333-333333333333', 'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Bebidas'),
    ('44444444-4444-4444-4444-444444444444', 'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Postres'),
    ('55555555-5555-5555-5555-555555555555', 'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Combos');

-- Productos = platos del menu de demo
INSERT INTO productos (tenant_id, nombre, precio, categoria_id) VALUES
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Empanadas de Pino (3 un)', 4500, '11111111-1111-1111-1111-111111111111'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Tabla de Picoteo', 8900, '11111111-1111-1111-1111-111111111111'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Lomo Saltado', 12900, '22222222-2222-2222-2222-222222222222'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Hamburguesa Clasica', 8900, '22222222-2222-2222-2222-222222222222'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Pizza Margarita', 9900, '22222222-2222-2222-2222-222222222222'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Ensalada Caesar', 7500, '22222222-2222-2222-2222-222222222222'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Bebida 500ml', 1500, '33333333-3333-3333-3333-333333333333'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Jugo Natural', 3500, '33333333-3333-3333-3333-333333333333'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Cerveza Artesanal', 4500, '33333333-3333-3333-3333-333333333333'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Brownie con Helado', 5500, '44444444-4444-4444-4444-444444444444'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Tres Leches', 4900, '44444444-4444-4444-4444-444444444444'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Combo Almuerzo (Plato + Bebida + Postre)', 14900, '55555555-5555-5555-5555-555555555555'),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Combo Familiar (4 Hamburguesas + 4 Bebidas)', 32900, '55555555-5555-5555-5555-555555555555');

INSERT INTO leads (tenant_id, nombre, email, telefono, canal, estado, valor_estimado) VALUES
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Carlos Morales', 'carlos@email.com', '+56912345678', 'WHATSAPP', 'NUEVO', 150000),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Maria Lopez', 'maria@email.com', '+56987654321', 'WEB', 'CONTACTADO', 250000),
    ('cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd', 'Pedro Soto', 'pedro@email.com', '+56911111111', 'WHATSAPP', 'EN_PROCESO', 80000);

INSERT INTO agente_config (tenant_id, system_prompt, umbral_confianza)
VALUES (
    'cbf23b4f-b37c-4fde-a0fb-df1dcd5a96dd',
    'Eres el asistente virtual del restaurante SiAvanza Demo. Ayudas a los clientes con pedidos, menu, reservas, horarios y delivery. Conoces todo el menu de memoria. Eres amable, rapido y cercano. Responde en espanol de Chile.',
    0.85
);

SELECT 'Database initialized successfully' AS result;
