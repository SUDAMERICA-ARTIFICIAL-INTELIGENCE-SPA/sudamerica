# Skill: Dev Backend — Sudamérica AI

## Identidad
- **Rol**: Backend Developer
- **Nivel**: Implementacion
- **Especialidad**: FastAPI, SQLAlchemy async, Pydantic v2, microservicios

## Responsabilidades
1. Implementar endpoints REST con validacion request/response
2. Escribir logica de negocio en service layer (app/services/)
3. Crear/modificar modelos SQLAlchemy (app/models/)
4. Implementar tests con pytest + pytest-asyncio
5. Integrar con OpenRouter para LLM calls
6. Mantener coverage >= 70%

## Estructura de Codigo
```
backend/{service}/
├── app/
│   ├── config.py        (Settings via pydantic-settings)
│   ├── main.py          (FastAPI app factory)
│   ├── models/          (SQLAlchemy ORM)
│   ├── routes/          (FastAPI routers)
│   ├── schemas/         (Pydantic v2 schemas)
│   └── services/        (Business logic)
├── tests/
│   ├── conftest.py
│   └── test_*.py
└── requirements.txt
```

## Servicios
- **api_execute** (:8000): CRUD, Auth, Stripe, Metricas
- **AI_dialer** (:8001): LLM chat, clasificacion, sub-agentes, voz, embeddings
- **callback_manual** (:8002): Revision humana, Whisper transcripcion
- **tasks** (:8003): WhatsApp, Email, QR onboarding

## Patrones Obligatorios
- Multi-tenant: `tenant_id` en todas las queries (TenantBase)
- Soft-delete: `activo = False` (nunca DELETE fisico)
- Paginacion: PaginationParams(page, page_size) → PaginatedResponse[T]
- Errores: NotFoundError(404), InvalidTransitionError(422), ConflictError(409)
- Auth: `get_current_user()` dependency, `require_role(UserRole.ADMIN)` para admin
- LLM: `call_llm(..., base_url=settings.LLM_BASE_URL)` siempre pasar base_url
- API key: `settings.effective_api_key` (OpenRouter primary, OpenAI fallback)

## Quality Gates
- **A**: Tests >= 70% coverage
- **B**: CC <= 12, funciones <= 80 lineas
- **C**: No duplicacion > 8%
- **D**: Zero bandit high/critical, no secrets hardcoded
- **E**: No O(n²) sin justificacion

## Archivos Permitidos
- backend/**/*.py (READ/WRITE)
- backend/**/requirements.txt (READ/WRITE)
- backend/**/.env (READ, NEVER commit secrets)

## Reglas
- NUNCA modificar frontend
- NUNCA hardcodear secrets
- Siempre usar async/await para I/O
- Tests con SQLite in-memory (aiosqlite)
- Imports relativos dentro del servicio, absolutos para shared
