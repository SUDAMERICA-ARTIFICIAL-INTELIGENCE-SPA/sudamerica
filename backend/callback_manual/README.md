# sudamerica-callback-manual

**Panel de Revision Humana** del backend de Sudamérica AI. Este microservicio permite a operadores humanos (ADMIN/ASESOR) revisar, aprobar, editar o rechazar respuestas generadas por la IA cuando la confianza es baja. Tambien integra transcripcion de audio via OpenAI Whisper.

## Datos del servicio

| Campo | Valor |
|-------|-------|
| Puerto | **8002** |
| Framework | FastAPI + Uvicorn |
| Base de datos | PostgreSQL 16 (asyncpg + SQLAlchemy 2.0) |
| Transcripcion | OpenAI Whisper API |
| Multi-tenant | RLS via `tenant_id` |

## Responsabilidades

- **Revision humana**: Cola de respuestas IA con confianza < 0.85 para que operadores las revisen
- **Acciones del operador**: Aprobar (envia tal cual), Editar (corrige y envia), Rechazar (descarta)
- **Transcripcion de audio**: Convierte audio a texto via OpenAI Whisper
- **Metricas de calidad**: Estadisticas de revision (pendientes, aprobadas, editadas, rechazadas, precision IA, tiempo promedio)

## Endpoints

```
POST   /api/v1/reviews                       Crear item de revision (llamado por api_execute)
GET    /api/v1/reviews/pendientes             Listar revisiones pendientes (ADMIN/ASESOR, paginado)
GET    /api/v1/reviews/stats                  Estadisticas de revision del dia
POST   /api/v1/reviews/{id}/aprobar           Aprobar respuesta IA
POST   /api/v1/reviews/{id}/editar            Editar respuesta + aprobar
POST   /api/v1/reviews/{id}/rechazar          Rechazar respuesta IA

POST   /api/v1/transcription                   Transcribir audio (Whisper, ruta canonica)
POST   /api/v1/reviews/transcription           Alias legacy temporal

GET    /health                                 Liveness probe
GET    /health/ready                           Readiness probe
```

## Flujo de revision humana

```
api_execute detecta confianza < 0.85
            │
            ▼
POST /api/v1/reviews (crea item pendiente)
            │
            ▼
Operador ve lista en GET /api/v1/reviews/pendientes
            │
            ├── APROBAR  → envia respuesta original a tasks :8003
            ├── EDITAR   → corrige texto, envia version editada a tasks :8003
            └── RECHAZAR → descarta, no se envia nada
            │
            ▼
tasks :8003 envia mensaje final al cliente (WhatsApp/Email)
```

## Estadisticas (`GET /api/v1/reviews/stats`)

```json
{
  "total_pendientes": 5,
  "aprobadas_hoy": 12,
  "editadas_hoy": 3,
  "rechazadas_hoy": 1,
  "tiempo_promedio_ms": 4500,
  "precision_ia": 0.75
}
```

La `precision_ia` se calcula como `aprobadas / (aprobadas + editadas + rechazadas)` del dia — mide que tan bien responde la IA sin necesidad de correccion humana.

## Conexion con otros microservicios

```
    ┌──────────────┐         ┌──────────────────────────────┐
    │ api_execute  │ ──────> │ >>> callback_manual :8002 <<< │
    │   :8000      │ confianza│  Revision Humana             │
    │ (confianza   │ < 0.85  │  Aprobar/Editar/Rechazar     │
    │  baja)       │         └──────────────┬───────────────┘
    └──────────────┘                        │
                                            │ Tras aprobar/editar
                                            ▼
                                   ┌──────────────┐
                                   │  tasks :8003 │
                                   │  Envia msg   │
                                   │  al cliente  │
                                   └──────────────┘
```

- **api_execute (:8000)**: Envia respuestas de baja confianza via `POST /api/v1/reviews` usando JWT interno con scope `reviews:create`.
- **tasks (:8003)**: Tras aprobar/editar, callback_manual notifica a tasks via `POST /api/v1/tasks/send-response` con la respuesta final + lead_id + tenant_id.
- **api_execute (:8000)**: No se comunica directamente, pero comparte la misma DB y JWT secret.
- **Frontend (frontend)**: El panel de revision en el frontend consulta los endpoints de pendientes y stats a traves de api_execute.
- **OpenAI Whisper**: Para transcripcion de audio (endpoint canonico `/api/v1/transcription`).

## Tabla de base de datos

### `revision_humana`

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID | FK a tenants (RLS) |
| `lead_id` | UUID | FK a leads (nullable) |
| `mensaje_original` | TEXT | Mensaje del cliente |
| `respuesta_ia` | TEXT | Respuesta generada por IA |
| `confianza` | NUMERIC(5,4) | Score de confianza (0-1) |
| `accion` | VARCHAR(20) | APROBAR, EDITAR, RECHAZAR |
| `respuesta_editada` | TEXT | Respuesta corregida (si accion=EDITAR) |
| `operador_id` | UUID | ID del operador que reviso |
| `procesado` | BOOLEAN | Si la revision esta completa |
| `tiempo_revision_ms` | INTEGER | Tiempo que tardo el operador (ms) |

## Estructura del proyecto

```
callback_manual/
├── app/
│   ├── main.py                  App factory + routers
│   ├── config.py                CallbackSettings desde .env
│   ├── models/
│   │   └── revision_humana.py   Modelo ORM
│   ├── routes/
│   │   ├── health.py            Health checks
│   │   ├── revision.py          CRUD revision humana
│   │   └── transcription.py     Whisper transcripcion
│   ├── schemas/
│   │   ├── revision.py          DTOs de revision
│   │   └── transcription.py     DTOs de transcripcion
│   └── services/
│       ├── revision_service.py      Logica de negocio + notificacion a tasks
│       └── transcription_service.py Integracion OpenAI Whisper
├── tests/                       3 modulos de tests
├── .env.example                 Template de variables de entorno
├── requirements.txt             Dependencias Python
└── Dockerfile                   Imagen Docker (python:3.12-slim, puerto 8002)
```

## Dependencia: shared package

Este servicio depende del paquete compartido `shared/` que provee:
- `database`: Engine async + session factory + RLS context
- `middleware`: TenantMiddleware, JWT auth, require_role (ADMIN, ASESOR)
- `models`: TenantBase (UUID + tenant_id + soft-delete + timestamps)
- `models.enums`: RevisionAccion (APROBAR, EDITAR, RECHAZAR), UserRole
- `schemas`: PaginatedResponse, PaginationParams, HealthResponse
- `utils`: HttpClient, NotFoundError, register_exception_handlers

## Setup local

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Completar OPENAI_API_KEY, JWT_SECRET_KEY, etc.

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar shared package
pip install -e ../shared

# 4. Levantar servicio
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Variables de entorno

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `JWT_SECRET_KEY` | Clave JWT para tokens de usuario |
| `JWT_ALGORITHM` | Algoritmo JWT (default: HS256) |
| `OPENAI_API_KEY` | API key de OpenAI (para Whisper) |
| `SERVICE_TASKS_URL` | URL de tasks (default: http://localhost:8003) |
| `CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY` | Clave HMAC propia del emisor `callback_manual` para JWT internos |
| `API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY`, `TASKS_INTERNAL_SERVICE_SECRET_KEY`, `CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY` | Claves confiadas por issuer para verificar JWT internos |

## Tests

```bash
export PYTHONPATH="$(pwd)/.."
pytest tests/ -v --tb=short
```
