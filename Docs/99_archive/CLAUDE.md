# Sudamérica AI MVP — Project Rules

> **IMPORTANT FOR ANY AI AGENT (Claude, GPT, Gemini, Copilot, etc.):**
> Read this ENTIRE file before writing any code. These are the project standards.

## Target Niche: GASTRONOMY (Restaurants, Cafes, Bars, Food Trucks)
- This is a CRM + AI assistant platform for restaurants and food businesses in Latin America
- The AI agent acts as a virtual waiter/assistant via WhatsApp and web chat
- Core flows: take orders, show menu, handle reservations, delivery info, quotes for events
- "Categorias" = menu sections (Entradas, Platos de Fondo, Bebidas, Postres, Combos)
- "Productos" = menu items (dishes, drinks, combos with prices)
- "Leads" = customers/clients of the restaurant
- All prompts, UI text, and agent responses must be in Spanish (Latin America)

## Architecture
- 5 FastAPI microservices: api_execute(:8000), AI_dialer(:8001), callback_manual(:8002), tasks(:8003), canales_service(:8004)
- Frontend: Next.js 14 + Mantine (frontend/)
- Multi-tenant via `tenant_id` + PostgreSQL RLS
- Shared code in `backend/shared/`
- LLM via OpenRouter (OpenAI-compatible API)
- WhatsApp via Evolution API (managed by canales_service)

## Quality Gates (NON-NEGOTIABLE)

### Gate A — Tests
- Coverage >= 70% (pytest --cov)
- All tests must pass before merge

### Gate B — Complexity
- Max cyclomatic complexity per function: 12
- Max function length: 80 lines

### Gate C — Duplication
- Max code duplication: 8%

### Gate D — Security
- Zero high/critical SAST findings (bandit)
- No hardcoded secrets in source code
- No SQL injection (use parameterized queries)

### Gate E — Performance
- No nested O(n²) loops without justification
- All DB queries must be tenant-scoped

## Conventions
- Plans: FREE (100 leads/mo, 3 users) / PRO (unlimited, 15 users)
- Lead FSM: NUEVO → CONTACTADO → EN_PROCESO → CONVERTIDO|DESCARTADO
- Venta total is immutable (server-computed)
- PATCH for updates (not PUT)
- Confidence threshold: >= 0.85 auto-send, < 0.85 human review
- All endpoints require JWT auth except /health
- Soft-delete via `activo` boolean

## Tech Stack
- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2
- PostgreSQL 16 + pgvector
- OpenRouter (AI_KEY) for LLM, ElevenLabs for voice
- Next.js 14, React 18, Mantine 7, TanStack Query
- Docker Compose for orchestration

## DB Tables (19)
tenants, usuarios, categorias, productos, leads, ventas, agente_config, revision_humana, stripe_events, ai_conversations, ai_embeddings, smart_alerts, sales_targets, evolution_instances, llm_provider_keys, contacts, sessions, tenant_knowledge, task_logs

## AI Agent Behavior Standards
- Default system prompt must be gastronomy-oriented (orders, menu, reservations, delivery)
- Classification intents: PEDIDO, MENU, RESERVA, DELIVERY, COTIZACION, CONSULTA, SEGUIMIENTO, SOPORTE, QUEJA, OTRO
- Sub-agent routing: PEDIDO/MENU/COTIZACION → Cotizador, SEGUIMIENTO → Seguimiento, rest → RAG
- Cotizador acts as a virtual waiter (shows menu, calculates totals, suggests combos)
- Seguimiento acts as a loyalty manager (remembers favorite orders, invites back)
- Onboarding collects: restaurant name, food type, hours, delivery zone, business description, tone
- Confidence >= 0.85 → auto-send via WhatsApp; < 0.85 → human review queue

## File Structure Standards
- Each service: `app/config.py`, `app/main.py`, `app/routes/`, `app/services/`, `app/models/`, `app/schemas/`
- Tests: `tests/` directory with `conftest.py` + `test_*.py` files
- Shared: `backend/shared/{database,middleware,models,schemas,utils}/`
- SQL schema: `backend/infra/001_schema.sql`, `002_rls_policies.sql`, `003_indexes.sql`
- Prompts: `backend/api_execute/app/prompts_ai.py` (centralized prompt engineering)

## LLM API Keys (Standard)
- **TWO keys only:** `OPENAI_API_KEY` (OpenAI direct) + `GEMINI_API_KEY` (Gemini)
- `AI_KEY` is REMOVED — do NOT use or reference it
- Default provider: `LLM_PROVIDER=openai`
- Embeddings: always via OpenAI (`OPENAI_API_KEY` + `text-embedding-3-small`)
- Per-tenant overrides: stored in `llm_provider_keys` table (encrypted), managed via sudamerica-admin
- Key rotation: done in sudamerica-admin → updates Cloud Run env vars + DB

## Frontends (TWO separate apps)
- **frontend** — Tenant-facing app (restaurants use this)
- **sudamerica-admin** — Internal admin panel (Sudamérica AI team, SUPERADMIN role)
- Requirements: `Docs/sudamerica-admin-requirements.md`

## Deploy Standards
- GCP Cloud Run + Cloud SQL (PostgreSQL 16)
- Docker images: `us-central1-docker.pkg.dev/{project}/sudamerica/{service}:latest`
- Backend build: `gcloud builds submit --config cloudbuild.yaml` from `backend/`
- NO auto-migrate in prod — new tables/columns require manual DDL in Cloud SQL
- Inter-service auth: service JWTs with scoped permissions
- CORS: dynamic from FRONTEND_URL env var
