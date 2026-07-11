# Sudamerica Admin — Requirements Document

> Internal admin panel for Sudamérica AI platform management.
> Separate frontend, deployed independently from frontend (tenant-facing app).

## 1. Purpose

Sudamerica Admin is the **internal operations dashboard** for the Sudamérica AI team.
It provides visibility and control over:
- All tenants (restaurants) and their users
- Platform-wide metrics and health
- API key management (OpenAI, Gemini) with real-time credit monitoring
- Billing and subscription status
- System configuration and feature flags

**This is NOT the tenant-facing app.** Tenants use frontend. Sudamerica Admin is for us.

## 2. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Next.js 15 (App Router) | Same as frontend, team knows it |
| UI | Mantine 7 | Consistent with frontend |
| State | TanStack Query + Zustand | Same pattern |
| Auth | JWT (role: SUPERADMIN) | New role, separate from tenant ADMIN |
| Charts | Recharts | Already in use |
| Tables | Mantine DataTable | Better for admin grids |
| Deploy | Cloud Run | Same infra |

## 3. Authentication

- **New role: `SUPERADMIN`** — not tied to any tenant, can see ALL tenants
- Login via email/password (same JWT flow as frontend)
- Access restricted to `@sudamerica.ai` email domain
- Session: 8h access token, 30d refresh
- All routes require SUPERADMIN role

### Backend Changes Required
- Add `SUPERADMIN` to `shared/models/enums.py` UserRole enum
- Add migration: `ALTER TYPE user_role ADD VALUE 'SUPERADMIN'`
- Add `superadmin_required` middleware in `shared/middleware/auth.py`
- Superadmin endpoints bypass RLS (no `SET LOCAL app.current_tenant_id`)

## 4. Pages & Features

### 4.1 Dashboard (`/`)
**Purpose:** Platform health at a glance

| Widget | Data Source | Priority |
|--------|-------------|----------|
| Total tenants (active/inactive) | `SELECT count(*) FROM tenants` | P0 |
| Total users across all tenants | `SELECT count(*) FROM usuarios` | P0 |
| Total leads this month | `SELECT count(*) FROM leads WHERE created_at >= month_start` | P0 |
| Total AI conversations today | `SELECT count(*) FROM ai_conversations WHERE created_at >= today` | P0 |
| Revenue (MRR from PRO plans) | `tenants WHERE plan='PRO'` * $15 | P1 |
| API credit usage (OpenAI/Gemini) | From API key monitoring (see 4.4) | P1 |
| Active WhatsApp instances | `SELECT count(*) FROM evolution_instances WHERE status='CONNECTED'` | P1 |
| Error rate (5xx last 24h) | Cloud Run metrics API | P2 |

**Layout:** Z-pattern with 4 KPI cards on top, 2 charts below (tenant growth, conversations/day)

### 4.2 Tenants (`/tenants`)
**Purpose:** View and manage all restaurant organizations

| Feature | Description | Priority |
|---------|-------------|----------|
| List all tenants | Table: nombre, plan, users count, leads count, created_at, status | P0 |
| Search/filter | By name, plan, date range | P0 |
| Tenant detail | Click row → drawer with full info | P0 |
| Edit tenant | Change plan (FREE↔PRO), max_users, max_leads_mes | P0 |
| Deactivate tenant | Soft-delete (activo=false) | P1 |
| View tenant users | List usuarios within tenant | P0 |
| View tenant config | agente_config, llm_provider_keys | P1 |
| Impersonate tenant | "View as tenant" → opens frontend with tenant context | P2 |

**Table columns:**
```
| Restaurante | Plan | Usuarios | Leads (mes) | WhatsApp | Creado | Estado |
```

### 4.3 Users (`/users`)
**Purpose:** View all users across all tenants

| Feature | Description | Priority |
|---------|-------------|----------|
| List all users | Table: nombre, email, tenant, role, last_login, activo | P0 |
| Search by email | Quick lookup | P0 |
| Filter by role | ADMIN, ASESOR, VIEWER, SUPERADMIN | P0 |
| Filter by tenant | Dropdown | P0 |
| Reset password | Generate temp password, send email | P1 |
| Deactivate user | Soft-delete | P1 |

### 4.4 API Keys (`/api-keys`)
**Purpose:** Manage LLM API keys and monitor credit usage

This is the **most critical page** — keys run out of credits constantly and need rotation.

| Feature | Description | Priority |
|---------|-------------|----------|
| Platform keys | OPENAI_API_KEY, GEMINI_API_KEY (env-level defaults) | P0 |
| Credit balance check | Call OpenAI/Gemini billing APIs to show remaining credits | P0 |
| Low credit alert | Visual warning when balance < $5 | P0 |
| Rotate key | Update key in Cloud Run env vars via API | P0 |
| Tenant keys | List per-tenant llm_provider_keys | P1 |
| Create tenant key | Add key to llm_provider_keys table (encrypted) | P1 |
| Key usage stats | Tokens consumed per key per day | P1 |
| Auto-failover | If OpenAI key exhausted, switch to Gemini automatically | P2 |

**Key Rotation Flow:**
1. Admin pastes new API key in form
2. System validates key by making a test API call
3. On success: update Cloud Run env var + update DB
4. Old key masked and archived

**Credit Check Integration:**
```
OpenAI: GET https://api.openai.com/v1/dashboard/billing/usage
Gemini: GET https://generativelanguage.googleapis.com/v1beta/models (validate key)
```

### 4.5 Metrics (`/metrics`)
**Purpose:** Platform-wide analytics

| Metric | Visualization | Priority |
|--------|---------------|----------|
| Tenants created per week | Line chart | P0 |
| Conversations per day | Bar chart | P0 |
| AI auto-resolution rate | Percentage gauge | P0 |
| Human review queue depth | Number + trend | P0 |
| Tokens consumed per day | Stacked bar (OpenAI vs Gemini) | P1 |
| Top tenants by usage | Leaderboard table | P1 |
| Lead conversion funnel | Funnel chart (NUEVO → CONVERTIDO) | P1 |
| Average response time | Line chart | P2 |
| WhatsApp delivery rate | Percentage | P2 |

### 4.6 WhatsApp (`/whatsapp`)
**Purpose:** Monitor Evolution API instances

| Feature | Description | Priority |
|---------|-------------|----------|
| Instance list | All evolution_instances with status | P0 |
| Connection status | CONNECTED/DISCONNECTED badge per tenant | P0 |
| QR regenerate | Force new QR for disconnected instance | P1 |
| Message volume | Messages sent/received per tenant per day | P1 |

### 4.7 System Config (`/config`)
**Purpose:** Global platform settings

| Feature | Description | Priority |
|---------|-------------|----------|
| Default AI prompt | Edit system-wide default system_prompt | P1 |
| Confidence threshold | Global default umbral_confianza | P1 |
| Plan limits | Edit FREE/PRO limits (max_leads, max_users) | P1 |
| Feature flags | Toggle features per plan | P2 |
| Cloud Run health | Service status (5 services) | P1 |

## 5. API Endpoints Required (Backend)

New endpoints in `api_execute` under `/api/v1/admin/`:

```
# Tenants
GET    /admin/tenants                → PaginatedResponse[TenantAdmin]
GET    /admin/tenants/{id}           → TenantAdmin (includes user count, lead count)
PATCH  /admin/tenants/{id}           → TenantAdmin
DELETE /admin/tenants/{id}           → 204 (soft-delete)

# Users
GET    /admin/users                  → PaginatedResponse[UserAdmin]
GET    /admin/users/{id}             → UserAdmin
PATCH  /admin/users/{id}             → UserAdmin
POST   /admin/users/{id}/reset-password → { temp_password }

# Metrics
GET    /admin/metrics/overview       → { tenants, users, leads, conversations, mrr }
GET    /admin/metrics/timeseries     → { data: [{date, tenants, leads, conversations}] }
GET    /admin/metrics/top-tenants    → [{ tenant, leads, conversations, revenue }]

# API Keys
GET    /admin/api-keys/platform      → { openai: {masked_key, balance, status}, gemini: {...} }
POST   /admin/api-keys/platform/rotate → { provider, new_key } → { success }
GET    /admin/api-keys/tenants       → [{ tenant, provider, masked_key, created_at }]
POST   /admin/api-keys/tenants       → { tenant_id, provider, api_key } → LLMProviderKey
GET    /admin/api-keys/usage         → [{ date, provider, tokens, cost }]

# WhatsApp
GET    /admin/whatsapp/instances     → [{ tenant, instance_name, status, phone }]
POST   /admin/whatsapp/{tenant_id}/reconnect → { qr_code }

# System
GET    /admin/system/health          → { services: [{name, url, status, latency}] }
PATCH  /admin/system/config          → { key, value }
```

All `/admin/*` endpoints require `SUPERADMIN` role.

## 6. Database Changes

```sql
-- Add SUPERADMIN role
ALTER TYPE user_role ADD VALUE 'SUPERADMIN';

-- Platform config table (key-value store for global settings)
CREATE TABLE platform_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by UUID REFERENCES usuarios(id)
);

-- API key audit log
CREATE TABLE api_key_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,  -- 'ROTATE', 'CREATE', 'DELETE', 'FAILOVER'
    performed_by UUID REFERENCES usuarios(id),
    old_key_masked VARCHAR(20),
    new_key_masked VARCHAR(20),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- No RLS on these tables (superadmin-only)
```

## 7. Deployment

| Property | Value |
|----------|-------|
| Service name | `sudamerica-admin` |
| Cloud Run URL | `https://sudamerica-admin-{hash}.us-central1.run.app` |
| Port | 3000 |
| Build | `gcloud builds submit --config cloudbuild-admin.yaml` |
| Env vars | `NEXT_PUBLIC_API_EXECUTE`, `NEXT_PUBLIC_API_DIALER` |
| Access | Restricted to `@sudamerica.ai` emails (no `--allow-unauthenticated`) |
| Memory | 512Mi, 1 CPU |
| Min instances | 0, Max 2 |

## 8. File Structure

```
sudamerica-admin/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx          # Sidebar + TopBar
│   │   ├── page.tsx            # Dashboard
│   │   ├── tenants/page.tsx
│   │   ├── users/page.tsx
│   │   ├── api-keys/page.tsx
│   │   ├── metrics/page.tsx
│   │   ├── whatsapp/page.tsx
│   │   └── config/page.tsx
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── layout/                 # AdminSidebar, AdminTopBar
│   ├── tenants/                # TenantTable, TenantDetail, TenantForm
│   ├── users/                  # UserTable, UserDetail
│   ├── api-keys/               # KeyCard, KeyRotateForm, CreditGauge
│   ├── metrics/                # Charts, Gauges, Leaderboard
│   └── whatsapp/               # InstanceTable, StatusBadge
├── hooks/
│   ├── useAdminTenants.ts
│   ├── useAdminUsers.ts
│   ├── useAdminMetrics.ts
│   ├── useAdminApiKeys.ts
│   └── useAdminWhatsApp.ts
├── lib/
│   ├── api.ts                  # Same pattern as frontend (apiFetch)
│   ├── auth.tsx                # SUPERADMIN guard
│   └── types.ts                # Admin-specific types
├── Dockerfile
├── cloudbuild-admin.yaml
├── package.json
├── tsconfig.json
└── biome.json
```

## 9. Priority Roadmap

### Phase 1 — MVP (1 week)
- [ ] Auth (SUPERADMIN login)
- [ ] Dashboard (KPIs)
- [ ] Tenants list + detail
- [ ] API Keys page (view + rotate)

### Phase 2 — Operations (1 week)
- [ ] Users management
- [ ] Metrics page
- [ ] WhatsApp instances
- [ ] Credit balance check

### Phase 3 — Advanced (1 week)
- [ ] Key usage stats
- [ ] Auto-failover
- [ ] Tenant impersonation
- [ ] System config

## 10. Standards (same as main project)

- TypeScript strict, no `any`, Biome linter
- Mantine 7 components, no Tailwind
- TanStack Query for server state, Zustand for client state
- `apiFetch()` with JWT auth and token refresh
- Conventional commits
- All text in Spanish (UI labels, button text, etc.)
- Responsive but desktop-first (admin panels are used on desktop)
