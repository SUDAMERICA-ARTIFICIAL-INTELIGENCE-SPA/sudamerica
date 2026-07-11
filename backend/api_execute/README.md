# sudamerica-api-execute

**Orquestador Principal** del backend de Sudamérica AI. Este microservicio es el punto de entrada de toda la plataforma: gestiona autenticacion, CRUD de todas las entidades de negocio, integracion con Stripe y metricas del dashboard.

## Datos del servicio

| Campo | Valor |
|-------|-------|
| Puerto | **8000** |
| Framework | FastAPI + Uvicorn |
| Base de datos | PostgreSQL 16 (asyncpg + SQLAlchemy 2.0) |
| Autenticacion | JWT (HS256) con access + refresh tokens |
| Multi-tenant | RLS via `tenant_id` en todas las tablas |

## Responsabilidades

- **Auth**: Registro de tenant + usuario admin, login, refresh token, verificacion de email
- **CRUD completo**: Tenants, Usuarios, Categorias, Productos, Leads, Ventas
- **Lead FSM**: Maquina de estados NUEVO -> CONTACTADO -> EN_PROCESO -> CONVERTIDO|DESCARTADO (422 en transicion invalida)
- **Ventas**: Total inmutable calculado server-side (`cantidad * precio_unitario`)
- **Stripe**: Checkout session para upgrade a PRO, webhook idempotente para subscription lifecycle
- **Metricas**: Revenue total, leads por canal/sector/estado, productos top, tasa de conversion
- **RBAC**: Endpoints protegidos por rol (ADMIN, ASESOR, VIEWER)

## Endpoints principales

```
POST   /api/v1/auth/register          Registrar tenant + admin
POST   /api/v1/auth/login             Login (devuelve JWT)
POST   /api/v1/auth/refresh           Refresh token

GET    /api/v1/tenants/me             Tenant actual
PATCH  /api/v1/tenants/me             Actualizar tenant (ADMIN)

CRUD   /api/v1/usuarios               Usuarios del tenant
CRUD   /api/v1/categorias             Categorias de productos
CRUD   /api/v1/productos              Productos (con filtros avanzados)
CRUD   /api/v1/leads                  Leads + FSM de estados
CRUD   /api/v1/ventas                 Ventas (solo CREATE + READ)

GET    /api/v1/metricas/revenue       Revenue total
GET    /api/v1/metricas/conversion    Tasa de conversion
GET    /api/v1/metricas/por-canal     Leads agrupados por canal
GET    /api/v1/metricas/por-sector    Leads agrupados por sector
GET    /api/v1/metricas/productos-top Top 10 productos vendidos
GET    /api/v1/metricas/leads-estado  Leads agrupados por estado

POST   /api/v1/stripe/create-checkout Crear sesion de pago Stripe
POST   /api/v1/stripe/webhook         Webhook de Stripe (idempotente)

GET    /health                        Liveness probe
GET    /health/ready                  Readiness probe (verifica DB)
```

## Planes

| Plan | Precio | Leads/mes | Usuarios |
|------|--------|-----------|----------|
| FREE | $0 | 100 | 3 |
| PRO | $15/mes | Ilimitados | 15 |

## Conexion con otros microservicios

```
                    ┌──────────────────────┐
                    │   frontend       │
                    │   (Next.js 14)       │
                    └──────────┬───────────┘
                               │ HTTPS
                               ▼
               ┌───────────────────────────────┐
               │  >>> api_execute :8000 <<<    │
               │  Auth, CRUD, Stripe, Metricas │
               └──┬──────────┬──────────┬──────┘
                  │          │          │
                  ▼          ▼          ▼
           ┌──────────┐ ┌──────────┐ ┌──────────┐
           │AI_dialer │ │callback  │ │  tasks   │
           │  :8001   │ │ _manual  │ │  :8003   │
           │ Chat, IA │ │  :8002   │ │WhatsApp  │
           └──────────┘ └──────────┘ └──────────┘
```

- **Frontend (frontend)**: Todas las llamadas REST del frontend llegan a este servicio. Es el unico punto de entrada HTTP para el cliente.
- **AI_dialer (:8001)**: api_execute envia mensajes al cerebro IA para clasificacion y chat. URL configurable via `SERVICE_AI_DIALER_URL`.
- **callback_manual (:8002)**: Recibe notificaciones cuando una respuesta IA tiene baja confianza. URL configurable via `SERVICE_CALLBACK_URL`.
- **tasks (:8003)**: Delega envio de email y trabajo asincronico post-callback. URL configurable via `SERVICE_TASKS_URL`.
- **canales_service (:8004)**: Owner de WhatsApp, QR y webhooks de Evolution API.

## Estructura del proyecto

```
api_execute/
├── app/
│   ├── main.py              App factory + routers
│   ├── config.py            Settings desde .env
│   ├── models/              7 modelos SQLAlchemy (Tenant, Usuario, Categoria, Producto, Lead, Venta, StripeEvent)
│   ├── routes/              10 routers (health, auth, tenants, usuarios, categorias, productos, leads, ventas, metricas, stripe)
│   ├── schemas/             8 modulos Pydantic (request/response DTOs)
│   └── services/            8 servicios de logica de negocio
├── tests/                   8 modulos de tests (pytest + pytest-asyncio)
├── .env.example             Template de variables de entorno
├── requirements.txt         Dependencias Python
└── Dockerfile               Imagen Docker (python:3.12-slim, puerto 8000)
```

## Dependencia: shared package

Este servicio depende del paquete compartido `shared/` que provee:
- `database`: Engine async + session factory + RLS context
- `middleware`: TenantMiddleware, JWT auth, RBAC (require_role)
- `models`: Base, TenantBase (UUID + tenant_id + soft-delete + timestamps)
- `schemas`: PaginatedResponse, PaginationParams, ErrorResponse
- `utils`: HttpClient, excepciones custom (NotFoundError, ForbiddenError, InvalidTransitionError)

## Setup local

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Completar JWT_SECRET_KEY, STRIPE_SECRET_KEY, etc.

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar shared package
pip install -e ../shared

# 4. Levantar servicio
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Variables de entorno

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `JWT_SECRET_KEY` | Clave secreta para firmar JWT |
| `JWT_ALGORITHM` | Algoritmo JWT (default: HS256) |
| `JWT_ACCESS_EXPIRATION_MINUTES` | Expiracion access token (default: 30) |
| `JWT_REFRESH_EXPIRATION_DAYS` | Expiracion refresh token (default: 7) |
| `BCRYPT_ROUNDS` | Rounds para hashing (default: 12) |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_PRO` | Stripe Price ID del plan PRO |
| `SERVICE_AI_DIALER_URL` | URL de AI_dialer (default: http://localhost:8001) |
| `SERVICE_CALLBACK_URL` | URL de callback_manual (default: http://localhost:8002) |
| `SERVICE_TASKS_URL` | URL de tasks (default: http://localhost:8003) |

## Tests

```bash
export PYTHONPATH="$(pwd)/.."
pytest tests/ -v --tb=short
```
