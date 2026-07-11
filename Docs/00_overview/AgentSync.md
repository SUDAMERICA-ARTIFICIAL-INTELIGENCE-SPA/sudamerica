# AgentSync — Sudamérica AI MVP

## Project Overview
CRM multi-tenant con IA para ventas B2B en Latinoamerica. 5 microservicios FastAPI + frontend Next.js.

---

## Current Sprint: MVP Funcional

### Acceptance Criteria
- [ ] Backend: 5 servicios levantan y responden /health
- [ ] AI_dialer: Chat endpoint funciona con OpenRouter
- [ ] AI_dialer: Clasificacion de intenciones retorna JSON valido
- [ ] AI_dialer: Sub-agentes (RAG, Cotizador, Seguimiento) integrados con datos reales
- [ ] callback_manual: Flujo aprobar/editar/rechazar funciona
- [ ] api_execute: CRUD completo para leads, productos, categorias, ventas
- [ ] api_execute: Auth register/login con JWT funciona
- [ ] Frontend: Conectado a API real (no mocks)
- [ ] Frontend: Login/Register UI funcional
- [ ] Docker: Todos los servicios levantan con docker-compose up

---

## API Contracts (SSOT = Backend)

### Auth
```
POST /api/v1/auth/register  → { tenant_id, access_token, refresh_token }
POST /api/v1/auth/login     → { access_token, refresh_token, user }
POST /api/v1/auth/refresh   → { access_token }
```

### Stripe / Billing
```
POST /api/v1/core/stripe/create-checkout
Body: { plan: "PLUS" | "PRO" }
→ { checkout_url, target_plan }

POST /api/v1/core/stripe/webhook
Headers: Stripe-Signature
→ { status: "processed" | "already_processed" }
```

### Leads
```
GET    /api/v1/leads                    → PaginatedResponse[Lead]
POST   /api/v1/leads                    → Lead
GET    /api/v1/leads/{id}               → Lead
PATCH  /api/v1/leads/{id}               → Lead
PATCH  /api/v1/leads/{id}/estado        → Lead (FSM validated)
```

### Productos
```
GET    /api/v1/productos                → PaginatedResponse[Producto]
POST   /api/v1/productos                → Producto
GET    /api/v1/productos/{id}           → Producto
PATCH  /api/v1/productos/{id}           → Producto
DELETE /api/v1/productos/{id}           → 204
```

### Ventas
```
GET    /api/v1/ventas                   → PaginatedResponse[Venta]
POST   /api/v1/ventas                   → Venta (total = qty * unit_price, immutable)
GET    /api/v1/ventas/{id}              → Venta
```

### AI Chat
```
POST   /api/v1/agente/chat             → ChatResponse { response, conversation_id, tokens_used, sub_agente_usado, confianza, sources }
POST   /api/v1/agente/classify          → { intencion, sector, confianza, sub_agente_sugerido }
```

`POST /api/v1/ai/conversations/import` â†’ `{ lead_id, imported_count, skipped_count }`

`GET /api/v1/ai/conversations/{lead_id}/messages?page=1&page_size=50` -> latest page of thread, chronological within page

### Metricas
```
GET    /api/v1/metricas/revenue         → { total_revenue, total_ventas }
GET    /api/v1/metricas/conversion      → { tasa_conversion }
GET    /api/v1/metricas/leads-estado    → [{ estado, count }]
```

### Admin
```
GET    /api/v1/admin/system/data-model  -> {
  generated_at,
  summary: { total_tables, total_columns, tenant_scoped_tables, total_relationships },
  enums: [{ name, values[] }],
  tables: [{
    name,
    model_name,
    description,
    tenant_scoped,
    has_soft_delete,
    columns: [{ name, type, nullable, primary_key, unique, default, foreign_key }],
    relations: [{ column, references_table, references_column, on_delete }],
    indexes: [{ name, columns[], unique }]
  }]
}
```

---

## Tech Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | OpenRouter | Compatible con OpenAI API, multiples modelos, key unica |
| Default Model | openai/gpt-4o-mini | Rapido y barato para testing |
| Database | PostgreSQL 16 + pgvector | RLS multi-tenant, embeddings nativas |
| Auth | JWT HS256 | Simple, stateless, 30min access + 7d refresh |
| Frontend State | TanStack Query | Cache, mutations, optimistic updates |

---

## Agent Assignments

| Agent | Scope | Files |
|-------|-------|-------|
| dev-backend | api_execute, AI_dialer, callback_manual, tasks, canales_service | backend/**/*.py |

## Service Boundaries

- `canales_service` owns WhatsApp onboarding, QR connection, instance settings and Evolution webhooks.
- `tasks` no longer owns QR or WhatsApp connection flows. It remains focused on async dispatch concerns.
- `evolution-api` runs as a dedicated Cloud Run service and is consumed only by `canales_service`.

## Channel Contracts

```
POST /api/v1/canales/qr/{tenant_id}                         -> { qr_code, instance_name, status }
GET  /api/v1/canales/qr/{tenant_id}/status                  -> { qr_code, instance_name, status }
POST /api/v1/canales/whatsapp/send                          -> { success, message_id }
POST /api/v1/canales/whatsapp/instance/{tenant_id}/settings -> { success, instance_name }
POST /api/v1/canales/whatsapp/instance/{tenant_id}/history/sync -> { success, instance_name, chats_scanned, chats_imported, chats_failed, messages_imported, messages_skipped }
POST /api/v1/canales/webhook/whatsapp                       -> { status, detail? }
```
Internal service auth:
- `callback_manual -> tasks/send-response` requires service JWT `aud=tasks`, caller `callback_manual`, scope `tasks:send_response`.
- `canales_service -> ai_dialer` requires service JWT scopes `config:read`, `contacts:resolve`, `chat:write`, `conversations:import`.
- `canales_service -> api_execute` requires service JWT scopes `leads:read`, `leads:write`.
- `ai_dialer -> callback_manual` requires service JWT `aud=callback_manual`, scope `reviews:create`.
- `callback_manual` exposes `POST /api/v1/transcription` as canonical transcription route and keeps `POST /api/v1/reviews/transcription` as a temporary legacy alias.
- `ai_dialer -> api_execute/productos` requires service JWT `aud=api_execute`, scope `productos:read`.
- Authenticated user requests use the JWT tenant as source of truth. If `X-Tenant-ID` is sent and does not match, the API returns `403`.

| dev-frontend | frontend | frontend/**/*.tsx |
| claude-bd | Database schema, migrations | backend/infra/*.sql, backend/shared/models/ |
| fullstack | Integration FE↔BE | Both frontend + backend |
| qa-sentinel | Quality gates, testing | tests/, all source |

---

## Product Standards (READ THIS — applies to any AI agent working on this codebase)

### Domain: Restaurant / Gastronomy
This platform serves restaurants, cafes, bars, food trucks, and catering businesses.
Every feature, prompt, and UI element must be oriented toward this niche.

### Vocabulary Mapping (Generic → Gastronomy)
| Generic CRM Term | Gastronomy Term | Example |
|-------------------|-----------------|---------|
| Categorias | Secciones del Menu | Entradas, Platos de Fondo, Bebidas, Postres, Combos |
| Productos | Platos / Items del Menu | Pizza Margarita ($9.900), Combo Almuerzo ($14.900) |
| Leads | Clientes del restaurante | Maria, +56912345678, pedido por WhatsApp |
| Ventas | Pedidos / Ordenes | 2x Hamburguesa + 2x Bebida = $20.800 |
| Cotizacion | Pedido grande / Catering | "Cotización para 50 personas, evento corporativo" |
| Seguimiento | Fidelizacion de clientes | "Hola Maria! Hace tiempo no te vemos, tenemos nuevas pizzas" |

### AI Intent Classification
| Intent | Description | Sub-agent |
|--------|-------------|-----------|
| PEDIDO | Customer wants to order food | COTIZADOR |
| MENU | Customer asks about the menu / available dishes | COTIZADOR |
| RESERVA | Customer wants to reserve a table | RAG |
| DELIVERY | Customer asks about delivery zone, cost, time | RAG |
| COTIZACION | Large order, catering, events | COTIZADOR |
| CONSULTA | General question (hours, location, payment methods) | RAG |
| SEGUIMIENTO | Status of an existing order | SEGUIMIENTO |
| SOPORTE | Problem with an order | RAG |
| QUEJA | Bad experience, complaint | RAG |
| OTRO | Unclassified | RAG |

### Onboarding Fields (New Restaurant Registration)
1. nombre — Owner's first name
2. apellido — Owner's last name
3. email — Restaurant or personal email
4. password — Secure password (8+ chars)
5. tenant_nombre — Restaurant name
6. tipo_comida — Cuisine type (pizza, sushi, burgers, etc.)
7. horario_atencion — Business hours (e.g. "11:00 a 23:00")
8. zona_delivery — Delivery zone (e.g. "10km radius", "pickup only")
9. descripcion_negocio — Brief description (what makes it special)
10. tono — AI tone: casual, formal, or mixto

Additional defaults created at registration:
- `plan = ESTANDAR`
- `config.sector = "gastronomia"`
- `config.onboarding.required = true`

### Code Standards (for any AI agent)
- **Language**: Python code in English, user-facing text in Spanish
- **HTTP verbs**: POST create, PATCH update (never PUT), DELETE soft-delete (activo=false)
- **Auth**: JWT HS256, 30min access + 7d refresh, /health is public
- **Multi-tenant**: ALL queries must include tenant_id, RLS enforced at DB level
- **Tests**: pytest async, conftest.py seeds test data, minimum 70% coverage
- **Prompts**: Centralized in `api_execute/app/prompts_ai.py`, dynamic with context injection
- **Error handling**: Return structured JSON `{success, data, error, meta}`
- **Naming**: snake_case for Python, camelCase for TypeScript/React
- **Commits**: Conventional commits (feat/fix/refactor/test/docs), Spanish or English OK

### Service Responsibilities (DO NOT cross boundaries)
| Service | Owns | Does NOT do |
|---------|------|-------------|
| api_execute | REST CRUD, Auth, Stripe, Metrics | LLM calls, WhatsApp |
| AI_dialer | LLM, Classification, Sub-agents, Embeddings | CRUD, Auth, Payments |
| callback_manual | Human review queue, Whisper transcription | LLM, CRUD |
| tasks | Async dispatch (email, WhatsApp send) | CRUD, LLM, Auth |
| canales_service | WhatsApp/QR connection, Evolution API | LLM, CRUD, Auth |

---

## Decision Log

| Date | Decision | By |
|------|----------|----|
| 2026-02-25 | Switch LLM from direct OpenAI to OpenRouter | tech-lead |
| 2026-02-25 | Add Supabase config for future DB migration | tech-lead |
| 2026-02-25 | Fix Cotizador: fetch real products from api_execute | dev-backend |
| 2026-02-25 | Fix Seguimiento: load lead data + conversation history | dev-backend |
| 2026-02-25 | Add CORS middleware to api_execute | dev-backend |
| 2026-03-10 | Move Evolution API to Cloud Run and pin official image `evoapicloud/evolution-api:v2.3.7` | dev-backend |
| 2026-03-12 | Add revision delivery tracking, tasks idempotency, and Prospectos real-time/cache fixes | fullstack |
| 2026-03-12 | Enforce service JWT scopes, tenant mismatch 403, encrypted `llm_provider_keys`, and explicit 1536-dim embeddings support | dev-backend |
| 2026-03-12 | Pivot to restaurant/gastronomy niche — all prompts, seed data, and classification adapted | project-manager |
| 2026-03-12 | Deploy canales_service to Cloud Run — WhatsApp is core channel for restaurants | dev-backend |
| 2026-03-15 | Stripe billing now supports `PLUS/PRO`, webhook syncs tenant plans, and onboarding progress is stored in `tenant.config` | fullstack |
| 2026-03-15 | Quality gate remediation sprint — fix all CC, security, duplication, and performance failures | project-manager |

---

## Sprint: Quality Gate Remediation (2026-03-15)

### Objetivo
Llevar TODOS los quality gates del backend a verde:
- **Gate A**: Tests ≥ 80% coverage, 0 failures
- **Gate B**: CC ≤ 10, funciones ≤ 30 lines, nesting ≤ 3
- **Gate C**: Duplicación ≤ 5%
- **Gate D**: 0 hallazgos SAST high/critical
- **Gate E**: 0 patrones O(n²), 0 N+1 queries, 0 queries sin scope

---

### Requisitos

- [REQ-QG-001] Reducir complejidad ciclomática de todas las funciones a CC ≤ 10
- [REQ-QG-002] Reducir largo de funciones a ≤ 30 líneas, nesting ≤ 3
- [REQ-QG-003] Eliminar duplicación de patrones CRUD (pagination, get-by-id, update, soft-delete)
- [REQ-QG-004] Resolver hallazgos de seguridad (webhook token en query param, temp password en response)
- [REQ-QG-005] Eliminar patrones N+1 y queries sin scope/limit
- [REQ-QG-006] Eliminar concatenación de strings con += en loops
- [REQ-QG-007] Agregar índices compuestos faltantes en esquema SQL
- [REQ-QG-008] Asegurar cobertura de tests ≥ 80% en todos los servicios

---

### Prioridades de Ejecución

#### P0 — Blockers (seguridad y correctitud)

| ID | Gate | Archivo | Función / Issue | Acción |
|----|------|---------|-----------------|--------|
| P0-1 | D | `canales_service/app/routes/whatsapp.py:278` | Webhook token aceptado via query param | Eliminar fallback `request.query_params.get("token")`, solo aceptar header `apikey` |
| P0-2 | D | `api_execute/app/routes/admin_users.py:54` | Temp password retornada en HTTP response | Enviar por email (SMTP via tasks), no retornar en JSON |
| P0-3 | E | `api_execute/app/routes/admin_whatsapp.py:24` | Query sin tenant_id filter (SUPERADMIN global) | Agregar paginación LIMIT/OFFSET (es admin, pero sin bound) |
| P0-4 | E | `api_execute/app/services/admin_service.py:62-97` | N+1: COUNT por tenant en loop (41 queries/page) | Reescribir con GROUP BY + subquery en una sola consulta |

#### P1 — Sprint (complejidad, CC > 10)

| ID | Gate | Archivo | Función | CC actual | Acción |
|----|------|---------|---------|-----------|--------|
| P1-1 | B | `AI_dialer/app/services/chat_service.py` | `chat()` | ~18-20 | Extraer `_build_system_prompt()`, `_route_classification()`, `_handle_confidence()` |
| P1-2 | B | `canales_service/app/services/whatsapp_service.py` | `process_incoming()` | ~16-18 | Extraer `_resolve_lead()`, `_handle_media_message()`, `_route_to_ai()` |
| P1-3 | B | `api_execute/app/services/ai_orchestrator.py` | `orchestrate_chat()` | ~14-16 | Extraer `_extract_order_json()`, `_attach_media()`, `_detect_menu_intent()` |
| P1-4 | B | `callback_manual/app/services/revision_service.py` | `_claim_revision()` | ~13 | Simplificar con early returns, extraer validación de conflictos |
| P1-5 | B | `AI_dialer/app/services/chat_service.py` | `_classify_and_route()` | ~12 | Simplificar condicionales con guard clauses |
| P1-6 | B | `api_execute/app/services/ai_orchestrator.py` | `_load_product_catalog_with_images()` | ~10 | Extraer loop de modifiers a helper |
| P1-7 | B | `canales_service/app/services/whatsapp_service.py` | `send_outbound()` | ~11 | Extraer `_send_media_message()`, `_import_history()` |

#### P2 — Backlog (duplicación y performance)

| ID | Gate | Archivo | Issue | Acción |
|----|------|---------|-------|--------|
| P2-1 | C | 11 archivos en `api_execute/services/` | Patrón list_paginated duplicado (~275 líneas) | Crear `backend/shared/services/crud.py` con `list_paginated()` |
| P2-2 | C | 12 archivos en `api_execute/services/` | Patrón get_by_id duplicado (~120 líneas) | Agregar `get_by_id()` a `shared/services/crud.py` |
| P2-3 | C | 12 archivos | Patrón update duplicado (~72 líneas) | Agregar `update_object()` a `shared/services/crud.py` |
| P2-4 | C | 10 archivos | Patrón soft_delete duplicado (~70 líneas) | Agregar `soft_delete()` a `shared/services/crud.py` |
| P2-5 | C | `producto_svc.py`, `modifier_svc.py` | `_escape_like()` duplicada | Mover a `shared/utils/sql_helpers.py` |
| P2-6 | E | `api_execute/app/services/comanda_svc.py:97` | N+1 modifier fetch en loop | Batch-fetch modifiers con `IN()` antes del loop |
| P2-7 | E | `api_execute/app/services/ai_orchestrator.py:187` | String += en loop | Usar `list.append()` + `"\n".join()` |
| P2-8 | E | `api_execute/app/routes/admin_api_keys.py:85` | Query sin LIMIT | Agregar paginación |
| P2-9 | E | `AI_dialer/app/services/knowledge_service.py:127` | Query sin LIMIT carga todo | Agregar `LIMIT 50` (early-exit por max_chars no basta) |
| P2-10 | E | `backend/infra/` | Índices compuestos faltantes | Crear `005_quality_indexes.sql` |

---

### Criterios de Aceptación

- [ ] **Gate B**: 0 funciones con CC > 10 (verificar con radon cc -n C)
- [ ] **Gate B**: 0 funciones con más de 30 líneas de código ejecutable
- [ ] **Gate B**: 0 funciones con nesting > 3 niveles
- [ ] **Gate C**: Duplicación CRUD eliminada — `shared/services/crud.py` usado en ≥ 8 servicios
- [ ] **Gate D**: Webhook token solo via header (0 query param auth)
- [ ] **Gate D**: Password reset no retorna password en HTTP response
- [ ] **Gate E**: 0 N+1 queries (admin_service, comanda_svc)
- [ ] **Gate E**: Todas las queries admin tienen LIMIT o paginación
- [ ] **Gate E**: 0 concatenación de strings con += en loops
- [ ] **Gate E**: Índices compuestos creados para columnas filtradas frecuentemente
- [ ] **Gate A**: Tests ≥ 80% coverage, todos pasan
- [ ] **Gate A**: Tests nuevos cubren las funciones refactorizadas

---

### Riesgos

| ID | Riesgo | Probabilidad | Impacto | Mitigación |
|----|--------|-------------|---------|------------|
| RISK-001 | Refactorizar `chat()` (90 líneas, núcleo del AI) rompe flujo de conversación | Alta | Crítico | Tests de integración exhaustivos ANTES de refactorizar. Mantener behavior idéntico, solo extraer funciones. |
| RISK-002 | Refactorizar `process_incoming()` (152 líneas) rompe recepción WhatsApp | Alta | Crítico | Probar con instancia Evolution API de staging. Webhook flow E2E test obligatorio. |
| RISK-003 | Extraer CRUD shared cambia firma de funciones en 11+ servicios | Media | Alto | Refactorizar UN servicio primero (categoria_svc, el más simple), validar, luego replicar. |
| RISK-004 | Cambiar webhook auth rompe Evolution API → canales_service | Media | Crítico | Coordinar con config de Evolution API: actualizar `WEBHOOK_URL` para enviar token en header, no query. Período de transición: aceptar ambos, luego deprecar query. |
| RISK-005 | Nuevos índices SQL en prod causan locks en tablas grandes | Baja | Medio | Crear índices con `CREATE INDEX CONCURRENTLY` en Cloud SQL fuera de horario pico. |
| RISK-006 | Eliminar temp password response rompe flow admin de sudamerica-admin | Media | Medio | Verificar si sudamerica-admin usa `ResetPasswordResponse.temp_password` antes de eliminar. Si sí, migrar UI primero. |

---

### Dependencias entre Tareas

```
P0-1 (webhook auth) → Requiere actualizar config Evolution API en Cloud Run
P0-2 (password reset) → Requiere SMTP configurado en tasks (pendiente: SMTP_HOST/PORT/USER/PASSWORD)
P2-1..P2-4 (shared CRUD) → P1-* puede usar los nuevos helpers
P2-10 (índices SQL) → Requiere acceso a Cloud SQL prod (DDL manual)
P1-1..P1-7 (CC refactors) → Cada uno independiente, pueden parallelizarse
```

### Orden de Ejecución Recomendado

1. **Fase 1 — Shared CRUD** (P2-1 a P2-5): Crear `shared/services/crud.py` primero para que los refactors de CC puedan aprovecharlo
2. **Fase 2 — CC Refactors** (P1-1 a P1-7): Extraer sub-funciones, tests en cada paso
3. **Fase 3 — Security** (P0-1, P0-2): Webhook header-only, password reset via email
4. **Fase 4 — Performance** (P0-3, P0-4, P2-6 a P2-9): N+1 fixes, pagination, string concat
5. **Fase 5 — Indexes + Tests** (P2-10, REQ-QG-008): DDL en Cloud SQL, coverage ≥ 80%

### Asignaciones

| Agente | Tareas | Estimado |
|--------|--------|----------|
| dev-backend | P0-1, P0-2, P0-3, P0-4, P1-1..P1-7, P2-6, P2-7, P2-8, P2-9 | — |
| fullstack | P2-1..P2-5 (shared CRUD library) | — |
| claude-bd | P2-10 (índices SQL) | — |
| qa-sentinel | Tests de cobertura, validación post-refactor | — |

---

## Tech Lead Architecture: Quality Gate Remediation (2026-03-15)

> Authored by: tech-lead
> Status: APPROVED — ready for implementation

---

### Decision 1: Shared CRUD Library Design

**Location**: `backend/shared/services/crud.py`

**Rationale**: 9 CRUD services in api_execute repeat identical patterns for `list_paginated`, `get_by_id`, `update`, and `soft_delete`. ~537 lines of duplication (~70-80% of CRUD code is boilerplate). A generic library with `Type[TenantBase]` parameterization eliminates this while keeping service-specific logic in each service file.

**Design**: Stateless async functions (NOT a class hierarchy). Each function takes the SQLAlchemy Model type as first arg. Services call these helpers and add custom logic around them.

```python
# backend/shared/services/crud.py
"""Generic tenant-scoped CRUD operations for TenantBase models."""

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from shared.models.base import TenantBase
from shared.schemas.base import PaginatedResponse
from shared.schemas.pagination import PaginationParams
from shared.utils.exceptions import NotFoundError


async def list_active(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    pagination: PaginationParams,
    *,
    extra_filters: Sequence[Any] = (),
    order_by: Any | None = None,
) -> PaginatedResponse:
    """Paginated list of active tenant-scoped records.

    Args:
        extra_filters: Additional SQLAlchemy where-clauses.
        order_by: Column or desc() expression. Default: created_at DESC.
    """
    base: Select = select(model).where(
        model.tenant_id == tenant_id,
        model.activo.is_(True),
    )
    for f in extra_filters:
        base = base.where(f)

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    if order_by is None:
        order_by = model.created_at.desc()
    rows = await db.execute(
        base.order_by(order_by).offset(pagination.offset).limit(pagination.page_size)
    )
    items = list(rows.scalars().all())
    return PaginatedResponse.build(
        items=items, total=total,
        page=pagination.page, page_size=pagination.page_size,
    )


async def get_by_id(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
    require_active: bool = True,
) -> TenantBase:
    """Fetch one record by (tenant_id, id). Raises NotFoundError."""
    clauses = [model.id == item_id, model.tenant_id == tenant_id]
    if require_active:
        clauses.append(model.activo.is_(True))
    result = await db.execute(select(model).where(*clauses))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise NotFoundError(label or model.__tablename__, str(item_id))
    return obj


async def update_fields(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    data: dict[str, Any],
    *,
    label: str | None = None,
) -> TenantBase:
    """PATCH semantics: update only provided fields."""
    obj = await get_by_id(db, model, tenant_id, item_id, label=label)
    for key, value in data.items():
        setattr(obj, key, value)
    await db.flush()
    return obj


async def soft_delete(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
) -> TenantBase:
    """Set activo=False."""
    obj = await get_by_id(db, model, tenant_id, item_id, label=label)
    obj.activo = False
    await db.flush()
    return obj


async def reactivate(
    db: AsyncSession,
    model: type[TenantBase],
    tenant_id: UUID,
    item_id: UUID,
    *,
    label: str | None = None,
) -> TenantBase:
    """Set activo=True (fetch even inactive records)."""
    obj = await get_by_id(
        db, model, tenant_id, item_id,
        label=label, require_active=False,
    )
    obj.activo = True
    await db.flush()
    return obj
```

**Migration example** — `categoria_svc.py` before/after:
```python
# BEFORE (duplicated 9x)
async def list_categorias(db, tenant_id, pagination):
    base = select(Categoria).where(
        Categoria.tenant_id == tenant_id,
        Categoria.activo.is_(True),
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = await db.execute(base.order_by(Categoria.created_at.desc()).offset(pagination.offset).limit(pagination.page_size))
    items = list(rows.scalars().all())
    return PaginatedResponse.build(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

# AFTER (1 line)
async def list_categorias(db, tenant_id, pagination):
    return await crud.list_active(db, Categoria, tenant_id, pagination)
```

**Shared utility** — `shared/utils/sql_helpers.py`:
```python
def escape_like(value: str) -> str:
    """Escape SQL LIKE special characters."""
    return value.replace("%", "\\%").replace("_", "\\_")
```

---

### Decision 2: Cyclomatic Complexity Refactors — Extraction Blueprints

Each extraction follows the **"preserve behavior, extract function"** pattern. NO logic changes, only structural decomposition.

#### P1-1: `chat()` in `chat_service.py` (lines 835-924, CC ~14)

**Current**: 90 lines, mixes prompt setup, classification routing, LLM call, confidence check, persistence.

**Extraction plan** (target: `chat()` ≤ 25 lines, CC ≤ 5):

| New function | Lines extracted | Responsibility |
|---|---|---|
| `_prepare_config(session, tenant_id, system_prompt_override, config)` | 862-879 | Resolve LLM config, apply system_prompt_override or KB context |
| `_classify_or_skip(session, tenant_id, message, cfg, ...)` | 886-890 | Returns (context, confianza, sub_agente, sources); skips if override |
| `_generate_or_reuse(message, context, sub_agente, cfg, ...)` | 892-904 | If COTIZADOR/SEGUIMIENTO reuse context; else call LLM |
| `_check_confidence_and_notify(settings, tenant_id, ...)` | 906-913 | Fire-and-forget to callback_manual if confianza < threshold |

**Refactored `chat()`**:
```python
async def chat(session, tenant_id, user_id, message, lead_id, canal, settings, ...) -> ChatResponse:
    if media_type == "audio" and media_url:
        message = await _transcribe_audio(media_url, message, settings, http_client)
    message = _sanitize_user_input(message)
    await _validate_ownership(session, tenant_id, lead_id, contact_id, request_session_id)

    cfg, llm_config, embedding_config, fallback_config = await _prepare_config(
        session, tenant_id, system_prompt_override, settings,
    )
    active_session_id = await _resolve_session(session, tenant_id, contact_id, ...)

    await _persist_and_broadcast(session, ..., "user", message, ...)

    context, confianza, sub_agente, sources = await _classify_or_skip(
        session, tenant_id, message, cfg, llm_config, embedding_config,
        settings, lead_id, system_prompt_override, http_client,
    )
    response_text, tokens_used = await _generate_or_reuse(
        message, context, sub_agente, cfg, llm_config, fallback_config,
        session, tenant_id, lead_id, active_session_id, system_prompt_override,
    )
    _check_confidence_and_notify(settings, tenant_id, lead_id, message, response_text, confianza, cfg, http_client)

    assistant_msg_id, _ = await _persist_and_broadcast(session, ..., "assistant", response_text, ...)
    await _update_session_tokens(session, tenant_id, active_session_id, tokens_used)
    return ChatResponse(...)
```

#### P1-2: `process_incoming()` in `whatsapp_service.py` (lines 326-478, CC ~15)

**Current**: 152 lines, mixes header building, lead resolution, media handling, AI forwarding, reply sending.

**Extraction plan** (target: `process_incoming()` ≤ 30 lines, CC ≤ 6):

| New function | Lines extracted | Responsibility |
|---|---|---|
| `_build_service_headers(settings, tenant_id)` | 340-375 | Returns dict with all 6 header sets |
| `_resolve_incoming_media(data, instance, settings, tenant_id)` | 394-417 | Handle media_url/media_type, audio download, build_history_msg |
| `_store_outbound_message(tenant_id, lead_id, msg, settings, headers)` | 421-430 | Store from_me messages as role=assistant |
| `_store_or_forward(message_text, lead_id, tenant_id, auto_respuesta, ...)` | 432-470 | Either store only (auto off) or forward to AI + send reply |
| `_send_ai_reply(ai_result, phone, instance_name, settings, lead_id)` | 461-476 | Send text reply + optional media + FSM progress |

**Refactored `process_incoming()`**:
```python
async def process_incoming(data, settings, db) -> dict:
    instance = await instance_service.lookup_by_instance_name(db, data["instance_name"])
    if instance is None:
        return {"status": "ignored", "reason": "unknown_instance"}

    phone = _normalize_phone(data["sender"])
    tenant_id = instance.tenant_id
    await set_tenant_context(db, str(tenant_id))

    headers = _build_service_headers(settings, tenant_id)
    lead_id = await _find_or_create_lead(phone, tenant_id, settings, **headers["api"])
    if lead_id is None:
        return {"status": "skipped", "reason": "lead_resolution_failed"}

    contact_id = await _resolve_contact(phone, tenant_id, settings, headers["ai_contact"])
    message_text, media_url, media_type, build_msg = _resolve_incoming_media(data, instance, settings, tenant_id)

    if data.get("from_me", False):
        return await _store_outbound_message(tenant_id, lead_id, build_msg("assistant", message_text), settings, headers)

    auto_respuesta = await _fetch_auto_respuesta_enabled(tenant_id, settings, headers["ai_config"])
    return await _store_or_forward(
        message_text, lead_id, tenant_id, auto_respuesta,
        settings, headers, contact_id, media_url, media_type,
        phone, instance.instance_name, build_msg,
    )
```

#### P1-3: `_load_product_catalog_with_images()` in `ai_orchestrator.py` (lines 123-193, CC ~10)

**Extraction plan** (target: ≤ 25 lines):

| New function | Lines extracted |
|---|---|
| `_fetch_modifier_map(session, tenant_id)` | 141-161 |
| `_format_product_line(product, modifier_map)` | 163-188 |

#### P1-6: `get_metrics_timeseries()` in `admin_service.py` (lines 345-391)

**Not a CC issue but an O(n) query issue.** Rewrite to single SQL:
```sql
SELECT
  d.day::date AS date,
  (SELECT count(*) FROM tenants WHERE created_at < d.day + interval '1 day') AS tenants,
  (SELECT count(*) FROM leads WHERE created_at >= d.day AND created_at < d.day + interval '1 day') AS leads,
  (SELECT count(*) FROM ai_conversations WHERE created_at >= d.day AND created_at < d.day + interval '1 day') AS conversations
FROM generate_series(:start::date, :end::date, '1 day') AS d(day)
ORDER BY d.day;
```
This replaces 90 queries with **1 query**.

#### P0-4 + N+1 fix: `list_tenants()` in `admin_service.py` (lines 41-101)

**Rewrite with LEFT JOIN + GROUP BY**:
```sql
SELECT t.*,
  COALESCE(uc.cnt, 0) AS user_count,
  COALESCE(lc.cnt, 0) AS lead_count
FROM tenants t
LEFT JOIN (
  SELECT tenant_id, count(*) AS cnt FROM usuarios WHERE activo = true GROUP BY tenant_id
) uc ON uc.tenant_id = t.id
LEFT JOIN (
  SELECT tenant_id, count(*) AS cnt FROM leads GROUP BY tenant_id
) lc ON lc.tenant_id = t.id
WHERE (:search IS NULL OR t.nombre ILIKE '%' || :search || '%')
  AND (:plan IS NULL OR t.plan = :plan)
ORDER BY t.created_at DESC
OFFSET :offset LIMIT :page_size;
```
Replaces 41 queries with **1 query**.

Same pattern for `list_users()` (JOIN tenant.nombre) and `get_top_tenants()` (GROUP BY + LIMIT in SQL).

---

### Decision 3: Security Fixes

#### P0-1: Webhook Token — Header Only

**File**: `canales_service/app/routes/whatsapp.py:278`

**Current** (INSECURE):
```python
incoming = request.headers.get("apikey", "") or request.query_params.get("token", "")
```

**Fix**:
```python
incoming = request.headers.get("apikey", "")
```

**Coordination required**: Evolution API sends webhook token in `apikey` header by default. The query param fallback was added as a workaround — it's no longer needed. Verify Evolution API config sends `apikey` header (it does by default in v2.3.7+).

**Transition**: Deploy with header-only, test webhook receipt, then update Evolution API config if needed.

#### P0-2: Temp Password — Do Not Return in Response

**File**: `api_execute/app/routes/admin_users.py:54-62`

**Current** (INSECURE):
```python
return ResetPasswordResponse(temp_password=temp_password)
```

**Fix** — Since SMTP is not yet configured (tasks service pending SMTP_HOST/PORT/USER/PASSWORD), use a pragmatic interim approach:

**Option A** (if SMTP ready): Send password via email through tasks service, return `{"status": "sent_to_email"}`.

**Option B** (interim, SMTP not ready): Keep the endpoint but:
1. Log the reset event (who, when)
2. Return a time-limited **one-time password reset token** instead of the raw password
3. Admin must use the token in a `/set-password` endpoint within 15 minutes

**Decision**: Implement **Option B** (reset token). Create `password_reset_tokens` in-memory dict with TTL (no new DB table needed for MVP). This is strictly better than returning cleartext passwords.

**Schema change**:
```python
class ResetPasswordResponse(BaseModel):
    reset_token: str  # One-time token, expires in 15 min
    expires_at: datetime
    # REMOVED: temp_password
```

---

### Decision 4: Performance Fixes

#### P0-3: Admin Queries Without LIMIT

**Files affected**:
- `admin_service.py:get_top_tenants()` — add `.limit(limit)` to initial query
- `admin_api_keys.py:85` — add `PaginationParams` dependency
- `admin_whatsapp.py:24` — add `PaginationParams` dependency

All admin list endpoints MUST accept `page` + `page_size` params (max 100).

#### P2-6: N+1 Modifier Fetch in `comanda_svc.py`

**Current**: Fetches modifiers per comanda_item in a loop.
**Fix**: Batch-fetch all modifier IDs with `WHERE id IN (all_modifier_ids)`, build lookup dict, then assign.

#### P2-7: String += in `ai_orchestrator.py`

**Current code** (line ~187): Already uses `lines.append()` + `"\n".join()`.
**Status**: After re-reading, this is **already correct** (list append pattern). No fix needed. ~~P2-7 is a false positive.~~

#### P2-9: Knowledge Service Without LIMIT

**File**: `AI_dialer/app/services/knowledge_service.py:127`
**Fix**: Add `LIMIT 100` to knowledge query. The `max_chars` early-exit is not sufficient — SQL should enforce the bound.

---

### Decision 5: Missing SQL Indexes

**New file**: `backend/infra/005_quality_indexes.sql`

```sql
-- Quality gate remediation indexes (2026-03-15)
-- Run with CREATE INDEX CONCURRENTLY in production

-- revision_humana: operador lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revision_humana_operador
  ON revision_humana(tenant_id, operador_id);

-- ai_conversations: usuario lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_conv_usuario
  ON ai_conversations(tenant_id, usuario_id);

-- smart_alerts: lead_id joins
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smart_alerts_lead
  ON smart_alerts(tenant_id, lead_id);

-- sessions: lead_id lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_lead
  ON sessions(tenant_id, lead_id);

-- comandas: tenant + estado for KDS queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comandas_tenant_estado
  ON comandas(tenant_id, estado);

-- comandas: fecha range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comandas_tenant_created
  ON comandas(tenant_id, created_at DESC);

-- comanda_items: comanda_id for JOIN performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comanda_items_comanda
  ON comanda_items(comanda_id);

-- modifier_groups: tenant + activo
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_modifier_groups_tenant_activo
  ON modifier_groups(tenant_id, activo);

-- producto_modifier_groups: product lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pmg_producto
  ON producto_modifier_groups(producto_id);
```

---

### API Contracts (Changes Only)

#### Password Reset (P0-2)
```
POST /api/v1/admin/users/{user_id}/reset-password
→ { reset_token: str, expires_at: datetime }   # CHANGED: no more temp_password

POST /api/v1/admin/users/set-password           # NEW
Body: { reset_token: str, new_password: str }
→ { status: "password_updated" }
```

#### Admin Endpoints (P0-3 — add pagination)
```
GET /api/v1/admin/api-keys?page=1&page_size=20  # CHANGED: was unbounded
GET /api/v1/admin/whatsapp?page=1&page_size=20   # CHANGED: was unbounded
```

All other contracts remain unchanged — the refactors are purely internal.

---

### Tareas de Ejecución (Detalladas)

| # | Tarea | Agente | Archivos | Dependencias | Gate |
|---|-------|--------|----------|-------------|------|
| 1 | Crear `shared/services/crud.py` con `list_active`, `get_by_id`, `update_fields`, `soft_delete`, `reactivate` | dev-backend | `backend/shared/services/crud.py` (NEW) | — | C |
| 2 | Crear `shared/utils/sql_helpers.py` con `escape_like()` | dev-backend | `backend/shared/utils/sql_helpers.py` (NEW) | — | C |
| 3 | Migrar `categoria_svc.py` a usar `shared/services/crud.py` (piloto) | dev-backend | `api_execute/app/services/categoria_svc.py` | 1 | C |
| 4 | Migrar restantes 8 servicios CRUD a usar shared crud | dev-backend | `producto_svc, lead_svc, venta_svc, mesa_svc, modifier_svc, comanda_svc, alerta_svc, sales_target_svc` | 3 (validated) | C |
| 5 | Refactor `chat()` → extract `_prepare_config`, `_classify_or_skip`, `_generate_or_reuse`, `_check_confidence_and_notify` | dev-backend | `AI_dialer/app/services/chat_service.py` | — | B |
| 6 | Refactor `process_incoming()` → extract `_build_service_headers`, `_resolve_incoming_media`, `_store_outbound_message`, `_store_or_forward`, `_send_ai_reply` | dev-backend | `canales_service/app/services/whatsapp_service.py` | — | B |
| 7 | Refactor `_load_product_catalog_with_images()` → extract `_fetch_modifier_map`, `_format_product_line` | dev-backend | `api_execute/app/services/ai_orchestrator.py` | — | B |
| 8 | Rewrite `list_tenants()`, `list_users()`, `get_top_tenants()` with JOIN + GROUP BY (single query each) | dev-backend | `api_execute/app/services/admin_service.py` | — | E |
| 9 | Rewrite `get_metrics_timeseries()` with `generate_series` single query | dev-backend | `api_execute/app/services/admin_service.py` | — | E |
| 10 | Remove webhook query param fallback (`_validate_webhook_token`) | dev-backend | `canales_service/app/routes/whatsapp.py:278` | — | D |
| 11 | Implement reset token flow (replace temp_password return) | dev-backend | `api_execute/app/services/admin_service.py`, `api_execute/app/routes/admin_users.py`, `api_execute/app/schemas/admin.py` | — | D |
| 12 | Add pagination to `admin_api_keys` and `admin_whatsapp` | dev-backend | `api_execute/app/routes/admin_api_keys.py`, `api_execute/app/routes/admin_whatsapp.py` | — | E |
| 13 | Fix N+1 modifier fetch in `comanda_svc.py` | dev-backend | `api_execute/app/services/comanda_svc.py` | — | E |
| 14 | Add LIMIT to knowledge service query | dev-backend | `AI_dialer/app/services/knowledge_service.py` | — | E |
| 15 | Create `005_quality_indexes.sql` + apply to Cloud SQL | claude-bd | `backend/infra/005_quality_indexes.sql` (NEW), Cloud SQL prod | — | E |
| 16 | Write tests for all refactored functions (target ≥ 80% coverage) | qa-sentinel | `tests/` across all services | 1-14 | A |
| 17 | Verify sudamerica-admin `ResetPasswordResponse` usage before deploy of task 11 | dev-frontend | `sudamerica-admin/hooks/useAdminUsers.ts` | before 11 | D |

### Execution Order (Dependency Graph)

```
Phase 1 (parallel):
  [1] shared/services/crud.py
  [2] shared/utils/sql_helpers.py
  [5] chat() refactor
  [6] process_incoming() refactor
  [7] _load_product_catalog refactor
  [8] admin N+1 fixes
  [9] timeseries fix
  [10] webhook token fix
  [12] admin pagination
  [13] comanda N+1 fix
  [14] knowledge LIMIT
  [15] SQL indexes
  [17] sudamerica-admin audit

Phase 2 (after [1]):
  [3] categoria_svc migration (pilot)

Phase 3 (after [3] validated):
  [4] remaining 8 service migrations

Phase 4 (after [17]):
  [11] password reset token flow

Phase 5 (after all above):
  [16] test coverage push to ≥ 80%
```

### Decisiones Técnicas (Sprint)

| Decision | Opción Elegida | Razón |
|---|---|---|
| CRUD library approach | Stateless functions (not OOP class hierarchy) | Simpler to adopt incrementally; services call `crud.list_active(db, Model, ...)` without inheritance. Avoids diamond problem if service extends multiple bases. |
| Password reset | One-time reset token (in-memory TTL dict) | SMTP not yet configured. Token approach is strictly better than cleartext password in response. No new DB table for MVP. |
| Admin N+1 fix | Raw SQL with JOIN + GROUP BY | SQLAlchemy ORM JOINs on cross-tenant admin queries add unnecessary complexity. Raw text() with parameterized queries is clearer and more performant for this use case. |
| Timeseries rewrite | `generate_series` CTE | PostgreSQL native, replaces O(days) Python loop with 1 query. Supported in PG 16. |
| Webhook auth transition | Immediate header-only (no transition period) | Evolution API v2.3.7+ sends `apikey` header by default. The query param was our workaround — safe to remove. |
| Indexes | `CREATE INDEX CONCURRENTLY` | Zero downtime, no table locks. Safe for production during low-traffic hours. |
| P2-7 (string +=) | **False positive — no fix needed** | After code review, `ai_orchestrator.py` already uses `list.append()` + `"\n".join()`. The += is only for single-line construction, not loop concatenation. |
