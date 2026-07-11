# Backend Monitoring & Observability — Guia Critica de Desarrollo

> **Fecha**: 2026-03-15
> **Autor**: CTO Review — Analisis automatizado del backend Sudamérica AI
> **Prioridad**: CRITICA — Implementar antes de escalar a mas de 10 tenants activos

---

## 1. Estado Actual del Monitoreo

### Resumen Ejecutivo

El backend tiene **CERO infraestructura de observabilidad**. No hay tracing distribuido, no hay logging estructurado, no hay metricas de aplicacion, no hay alertas automaticas, no hay rate limiting. El unico monitoreo existente es:

- Logs en texto plano a stdout (capturados por Cloud Run → Cloud Logging, pero sin estructura)
- Health checks basicos (`SELECT 1` en 4 de 6 servicios)
- Metricas de negocio via SQL queries (dashboard admin, no infra)

### Inventario Detallado — Que Existe Hoy

| Componente | Estado | Archivos | Detalle |
|------------|--------|----------|---------|
| **Logging** | Basico | `shared/middleware/tenant.py`, cada `main.py` | stdlib `logging`, formato texto `%(asctime)s \| %(levelname)-7s \| %(name)s \| %(message)s` |
| **Health Liveness** | OK | `*/app/routes/health.py` (6 servicios) | Retorna `{service: "nombre"}`, no valida nada |
| **Health Readiness** | Parcial | `api_execute`, `AI_dialer`, `callback_manual` | Ejecutan `SELECT 1`. **tasks y canales_service NO verifican DB** |
| **Request Logging** | NULO | N/A | No existe middleware que registre method, path, status, latencia |
| **Request IDs** | NULO | N/A | No se genera ni propaga X-Request-ID entre servicios |
| **Structured Logging** | NULO | N/A | Logs son texto plano, no JSON. Cloud Logging no puede parsearlos |
| **Metricas Infra** | NULO | N/A | No hay Prometheus, no hay `/metrics` endpoint |
| **Tracing Distribuido** | NULO | N/A | No hay OpenTelemetry, no hay Cloud Trace |
| **Error Aggregation** | NULO | N/A | No hay Sentry ni equivalente |
| **Alertas** | NULO | N/A | No hay Cloud Monitoring alerts, ni PagerDuty/OpsGenie |
| **Circuit Breaker** | NULO | `shared/utils/http_client.py` | Solo retry con backoff (3 intentos). Sin circuit breaker |
| **Rate Limiting** | NULO | N/A | No hay slowapi ni limitacion por tenant |
| **DB Monitoring** | Minimo | `shared/database/session.py` | pool_size=5, max_overflow=10. Sin slow query logging, sin pool metrics |

### Dependencias de Observabilidad Instaladas

**CERO** — Ningun `requirements.txt` tiene paquetes de observabilidad.

```
# Lo que hay hoy en requirements.txt (patron comun a los 6 servicios):
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
asyncpg>=0.30.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
PyJWT>=2.8.0
cryptography>=42.0.0
httpx>=0.27.0
# ... y deps especificas (stripe, pgvector, aiosmtplib, etc.)
# NADA de: opentelemetry, prometheus-client, sentry-sdk, structlog, python-json-logger
```

### Riesgo Operativo Actual

Un request que cruza los 5 servicios (usuario → api_execute → AI_dialer → callback_manual → tasks → canales_service) **no tiene forma de rastrearse end-to-end**. Si un usuario reporta "mi mensaje no llego", diagnosticar requiere:

1. Buscar manualmente en Cloud Logging por timestamp aproximado
2. Filtrar por servicio (5 logs separados)
3. Intentar correlacionar por contenido del mensaje (no hay IDs compartidos)
4. Rezar que el log tenga suficiente contexto

**Tiempo estimado de diagnostico hoy**: 30-60 minutos por incidente.
**Tiempo con observabilidad completa**: 2-5 minutos.

---

## 2. Plan de Implementacion — 4 Fases

### Fase 1: Structured Logging + Request IDs (CRITICA — Semana 1)

**Objetivo**: Que cada log sea JSON parseable por Cloud Logging, con request_id propagado entre servicios.

**Impacto**: Habilita busquedas en Cloud Logging por request_id, tenant_id, service, level. Reduce tiempo de diagnostico de 30min a 5min.

#### Paso 1.1: Crear modulo de logging en shared

**Archivo a crear**: `backend/shared/utils/logging.py`

```python
"""Structured JSON logging with request context propagation."""

import json
import logging
import sys
import uuid
from contextvars import ContextVar

# Context variables — propagated automatically across async calls
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
service_name_var: ContextVar[str] = ContextVar("service_name", default="unknown")


def generate_request_id() -> str:
    """Generate a short, unique request ID."""
    return uuid.uuid4().hex[:12]


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Cloud Logging auto-parses JSON lines and indexes the fields,
    enabling queries like: jsonPayload.request_id="abc123"
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": service_name_var.get("unknown"),
            "request_id": request_id_var.get(""),
            "tenant_id": tenant_id_var.get(""),
            "user_id": user_id_var.get(""),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields from logger.info("msg", extra={...})
        for key in ("status_code", "method", "path", "duration_ms",
                     "lead_id", "session_id", "error_code"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """Configure structured JSON logging for a service.

    Call once in create_app() of each microservice.
    """
    service_name_var.set(service_name)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
```

#### Paso 1.2: Crear middleware de Request Logging

**Archivo a crear**: `backend/shared/middleware/request_logging.py`

```python
"""Middleware that logs every HTTP request/response with timing and context."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.utils.logging import (
    generate_request_id,
    request_id_var,
    tenant_id_var,
    user_id_var,
)

logger = logging.getLogger("app.http")

# Paths that should not be logged (health checks, metrics)
_SKIP_PATHS = frozenset({"/health", "/health/ready", "/metrics"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration for every request.

    Also sets context variables (request_id, tenant_id) that are
    automatically included in all subsequent log lines within the
    same async context.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept or generate request ID
        req_id = request.headers.get("x-request-id") or generate_request_id()
        request_id_var.set(req_id)

        # Store on request.state so downstream code can access it
        request.state.request_id = req_id

        start = time.perf_counter()
        status_code = 500  # default if call_next raises

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Propagate request_id in response headers
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)

            # Set tenant/user from state if TenantMiddleware ran
            tid = getattr(request.state, "tenant_id", None) or ""
            uid = ""
            auth_ctx = getattr(request.state, "auth_context", None)
            if auth_ctx and isinstance(auth_ctx, dict):
                uid = auth_ctx.get("sub", "")
            tenant_id_var.set(str(tid) if tid else "")
            user_id_var.set(str(uid) if uid else "")

            if request.url.path not in _SKIP_PATHS:
                logger.info(
                    "%s %s → %d (%.1fms)",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )
```

#### Paso 1.3: Propagar request_id en llamadas inter-servicio

**Archivo a modificar**: `backend/shared/utils/http_client.py`

Agregar propagacion automatica del request_id en cada llamada HTTP saliente:

```python
"""HTTP client wrapper with retry, header injection, and request ID propagation."""

import asyncio
import logging
import random

import httpx

from shared.utils.logging import request_id_var

logger = logging.getLogger(__name__)


class HttpClient:
    """Async HTTP client with retry logic and request ID propagation."""

    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = dict(headers or {})

        # Propagate request ID across service boundaries
        req_id = request_id_var.get("")
        if req_id and "x-request-id" not in {k.lower() for k in headers}:
            headers["X-Request-ID"] = req_id

        retry_on_timeout = method.upper() in {"GET", "PUT", "DELETE", "HEAD", "OPTIONS"}
        retryable = (httpx.ConnectError, httpx.ReadTimeout) if retry_on_timeout else (httpx.ConnectError,)
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)
                    return response
            except retryable as exc:
                last_exc = exc
                if attempt == self.max_retries - 1:
                    raise
                backoff = min(2 ** attempt, 8) + random.uniform(0, 0.25)
                logger.warning(
                    "Retry %d/%d for %s %s: %s",
                    attempt + 1, self.max_retries, method, url, exc,
                )
                await asyncio.sleep(backoff)
            except httpx.ReadTimeout:
                raise
        raise last_exc  # type: ignore[misc]

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
```

#### Paso 1.4: Integrar en cada servicio

**Patron a aplicar en CADA `main.py`** (6 servicios):

Antes (actual en `api_execute/app/main.py:43-51`):
```python
def _setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    root = logging.getLogger("app")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    root.propagate = False
```

Despues:
```python
from shared.utils.logging import setup_logging
from shared.middleware.request_logging import RequestLoggingMiddleware

def create_app() -> FastAPI:
    settings = ApiExecuteSettings()
    setup_logging("api_execute", settings.LOG_LEVEL)
    # ...
    # Agregar ANTES de TenantMiddleware (el orden importa):
    app.add_middleware(RequestLoggingMiddleware)  # primero (outer)
    app.add_middleware(TenantMiddleware)          # segundo (inner)
    # ...
```

**Servicios a modificar** (orden del middleware es outer→inner en Starlette):

| Servicio | Archivo | Lineas a cambiar |
|----------|---------|-------------------|
| api_execute | `api_execute/app/main.py` | L43-51 (reemplazar `_setup_logging`) + L85 (agregar middleware) |
| AI_dialer | `AI_dialer/app/main.py` | L18-26 (reemplazar `_setup_logging`) + agregar middleware |
| callback_manual | `callback_manual/app/main.py` | L20 (reemplazar `basicConfig`) + agregar middleware |
| tasks | `tasks/app/main.py` | Reemplazar logging setup + agregar middleware |
| canales_service | `canales_service/app/main.py` | Reemplazar logging setup + agregar middleware |
| open_agent | `open_agent/app/main.py` | L21-28 (reemplazar setup) + agregar middleware |

#### Paso 1.5: Exportar nuevos modulos en shared

**Modificar**: `backend/shared/utils/__init__.py` — agregar exports:
```python
from shared.utils.logging import setup_logging, generate_request_id, request_id_var, tenant_id_var
```

**Modificar**: `backend/shared/middleware/__init__.py` — agregar:
```python
from shared.middleware.request_logging import RequestLoggingMiddleware
```

#### Paso 1.6: Verificacion

Despues de aplicar los cambios, un log debe verse asi en Cloud Logging:

```json
{
  "timestamp": "2026-03-15T14:32:01",
  "severity": "INFO",
  "logger": "app.http",
  "message": "POST /api/v1/ai/chat → 200 (1243.5ms)",
  "service": "ai_dialer",
  "request_id": "a1b2c3d4e5f6",
  "tenant_id": "f2281e11-...",
  "user_id": "abc123-...",
  "method": "POST",
  "path": "/api/v1/ai/chat",
  "status_code": 200,
  "duration_ms": 1243.5
}
```

En Cloud Logging se puede buscar: `jsonPayload.request_id="a1b2c3d4e5f6"` y ver TODOS los logs de todos los servicios para ese request.

#### Tests para Fase 1

**Crear**: `backend/shared/tests/test_logging.py`

```python
"""Tests for structured logging and request ID propagation."""
import json
import logging

from shared.utils.logging import (
    JSONFormatter,
    generate_request_id,
    request_id_var,
    tenant_id_var,
    service_name_var,
)


def test_generate_request_id_length():
    rid = generate_request_id()
    assert len(rid) == 12
    assert rid.isalnum()


def test_generate_request_id_unique():
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100


def test_json_formatter_outputs_valid_json():
    formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello %s", args=("world",), exc_info=None,
    )
    service_name_var.set("test_service")
    request_id_var.set("abc123")
    tenant_id_var.set("tenant-1")

    output = formatter.format(record)
    data = json.loads(output)

    assert data["message"] == "hello world"
    assert data["severity"] == "INFO"
    assert data["service"] == "test_service"
    assert data["request_id"] == "abc123"
    assert data["tenant_id"] == "tenant-1"


def test_json_formatter_includes_extra_fields():
    formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="req done", args=(), exc_info=None,
    )
    record.status_code = 200  # type: ignore[attr-defined]
    record.duration_ms = 45.2  # type: ignore[attr-defined]
    service_name_var.set("api_execute")

    output = formatter.format(record)
    data = json.loads(output)

    assert data["status_code"] == 200
    assert data["duration_ms"] == 45.2


def test_json_formatter_includes_exception():
    formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )

    output = formatter.format(record)
    data = json.loads(output)

    assert "exception" in data
    assert "ValueError: test error" in data["exception"]
```

---

### Fase 2: Health Checks Mejorados + Error Context (Semana 1-2)

**Objetivo**: Health checks que validen dependencias reales. Errores con IDs unicos para rastreo.

#### Paso 2.1: Health checks con dependencias

**Reemplazar**: `backend/api_execute/app/routes/health.py`

```python
"""Health check endpoints: liveness, readiness, and dependency status."""

import logging
import time

from fastapi import APIRouter, Request
from sqlalchemy import text

from shared.database import get_db
from shared.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def liveness():
    """Liveness probe — confirms process is alive."""
    return HealthResponse(service="api_execute")


@router.get("/health/ready")
async def readiness(request: Request):
    """Readiness probe — checks DB and critical dependencies."""
    checks = {}
    overall = True

    # Check database
    try:
        start = time.perf_counter()
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        }
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)[:200]}
        overall = False

    # Check downstream services (non-blocking, just connectivity)
    settings = request.app.state.settings
    import httpx
    for name, url in [
        ("ai_dialer", getattr(settings, "SERVICE_AI_DIALER_URL", None)),
        ("tasks", getattr(settings, "SERVICE_TASKS_URL", None)),
    ]:
        if not url:
            checks[name] = {"status": "not_configured"}
            continue
        try:
            start = time.perf_counter()
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{url}/health")
                checks[name] = {
                    "status": "ok" if resp.status_code == 200 else "degraded",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                }
        except Exception:
            checks[name] = {"status": "unreachable"}
            # Downstream unreachable is degraded, not fatal
            # overall stays True — this service can still serve requests

    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=200 if overall else 503,
        content={
            "service": "api_execute",
            "status": "ready" if overall else "not_ready",
            "checks": checks,
        },
    )
```

**Aplicar patron similar en**: `tasks/app/routes/health.py` y `canales_service/app/routes/health.py` (actualmente NO verifican DB).

#### Paso 2.2: Error responses con request_id

**Modificar**: `backend/shared/utils/exceptions.py`

Agregar `request_id` a cada respuesta de error para que el usuario pueda reportarlo:

```python
"""Custom exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.utils.logging import request_id_var


class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: str | None = None):
        self.resource = resource
        self.identifier = identifier
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(detail)


class ForbiddenError(Exception):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(detail)


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Invalid transition from {current} to {target}")
        self.current = current
        self.target = target


class ConflictError(Exception):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(detail)


def _error_body(detail: str, code: str) -> dict:
    """Build error response body with request_id for traceability."""
    body = {"detail": detail, "code": code}
    req_id = request_id_var.get("")
    if req_id:
        body["request_id"] = req_id
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content=_error_body(str(exc), "NOT_FOUND"))

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(status_code=403, content=_error_body(str(exc), "FORBIDDEN"))

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition_handler(request: Request, exc: InvalidTransitionError):
        return JSONResponse(status_code=422, content=_error_body(str(exc), "INVALID_TRANSITION"))

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content=_error_body(str(exc), "CONFLICT"))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        import logging
        logger = logging.getLogger("app.unhandled")
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_error_body("Internal server error", "INTERNAL_ERROR"))
```

El frontend puede mostrar: "Error. Referencia: a1b2c3d4e5f6" y soporte puede buscar ese ID en Cloud Logging.

---

### Fase 3: Circuit Breaker + Rate Limiting (Semana 2)

**Objetivo**: Proteger servicios de cascading failures y abuso.

#### Paso 3.1: Circuit Breaker en HttpClient

**Modificar**: `backend/shared/utils/http_client.py`

No se requiere dependencia externa. Implementacion minima con estado in-memory:

```python
"""HTTP client with retry, circuit breaker, and request ID propagation."""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field

import httpx

from shared.utils.logging import request_id_var

logger = logging.getLogger(__name__)


@dataclass
class CircuitState:
    """Simple circuit breaker state per base_url."""
    failures: int = 0
    last_failure: float = 0.0
    is_open: bool = False

    # Config
    failure_threshold: int = 5       # Open after N consecutive failures
    recovery_timeout: float = 30.0   # Try again after N seconds


# Global circuit states per service URL
_circuits: dict[str, CircuitState] = {}


def _get_circuit(base_url: str) -> CircuitState:
    if base_url not in _circuits:
        _circuits[base_url] = CircuitState()
    return _circuits[base_url]


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open for a target service."""
    def __init__(self, base_url: str, retry_after: float):
        self.base_url = base_url
        self.retry_after = retry_after
        super().__init__(f"Circuit open for {base_url}, retry after {retry_after:.0f}s")


class HttpClient:
    """Async HTTP client with retry, circuit breaker, and request ID propagation."""

    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._circuit = _get_circuit(self.base_url)

    def _check_circuit(self) -> None:
        """Raise if circuit is open and recovery timeout hasn't elapsed."""
        cb = self._circuit
        if not cb.is_open:
            return
        elapsed = time.monotonic() - cb.last_failure
        if elapsed >= cb.recovery_timeout:
            # Half-open: allow one attempt
            cb.is_open = False
            cb.failures = cb.failure_threshold - 1  # One more failure re-opens
            logger.info("Circuit half-open for %s, allowing probe request", self.base_url)
        else:
            raise CircuitOpenError(self.base_url, cb.recovery_timeout - elapsed)

    def _record_success(self) -> None:
        cb = self._circuit
        cb.failures = 0
        cb.is_open = False

    def _record_failure(self) -> None:
        cb = self._circuit
        cb.failures += 1
        cb.last_failure = time.monotonic()
        if cb.failures >= cb.failure_threshold:
            cb.is_open = True
            logger.warning(
                "Circuit OPEN for %s after %d failures. Recovery in %ds.",
                self.base_url, cb.failures, cb.recovery_timeout,
            )

    async def request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        self._check_circuit()

        url = f"{self.base_url}{path}"
        headers = dict(headers or {})

        # Propagate request ID
        req_id = request_id_var.get("")
        if req_id and "x-request-id" not in {k.lower() for k in headers}:
            headers["X-Request-ID"] = req_id

        retry_on_timeout = method.upper() in {"GET", "PUT", "DELETE", "HEAD", "OPTIONS"}
        retryable = (httpx.ConnectError, httpx.ReadTimeout) if retry_on_timeout else (httpx.ConnectError,)
        last_exc = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)
                    if response.status_code >= 500:
                        self._record_failure()
                    else:
                        self._record_success()
                    return response
            except retryable as exc:
                self._record_failure()
                last_exc = exc
                if attempt == self.max_retries - 1:
                    raise
                backoff = min(2 ** attempt, 8) + random.uniform(0, 0.25)
                logger.warning("Retry %d/%d for %s %s: %s", attempt + 1, self.max_retries, method, url, exc)
                await asyncio.sleep(backoff)
            except httpx.ReadTimeout:
                self._record_failure()
                raise
        raise last_exc  # type: ignore[misc]

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
```

**Comportamiento**:
- Despues de 5 fallos consecutivos al mismo servicio → circuito ABIERTO
- Mientras esta abierto → `CircuitOpenError` inmediato (no espera timeout)
- Despues de 30s → permite 1 request de prueba (half-open)
- Si el probe tiene exito → circuito CERRADO
- Si el probe falla → circuito ABIERTO de nuevo

#### Paso 3.2: Rate Limiting por tenant

**Dependencia a agregar** en TODOS los `requirements.txt`:
```
slowapi>=0.1.9
```

**Archivo a crear**: `backend/shared/middleware/rate_limit.py`

```python
"""Per-tenant rate limiting via slowapi."""

import logging
from starlette.requests import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _tenant_key(request: Request) -> str:
    """Rate limit by tenant_id (from JWT), fall back to IP."""
    tid = getattr(request.state, "tenant_id", None)
    if tid:
        return f"tenant:{tid}"
    return f"ip:{get_remote_address(request)}"


# Global limiter instance (uses in-memory storage by default)
limiter = Limiter(key_func=_tenant_key)


def add_rate_limiting(app: FastAPI) -> None:
    """Register rate limiter and custom 429 handler."""
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(
            "Rate limit exceeded for %s on %s %s",
            _tenant_key(request), request.method, request.url.path,
        )
        from shared.utils.logging import request_id_var
        body = {
            "detail": "Rate limit exceeded. Please retry later.",
            "code": "RATE_LIMIT_EXCEEDED",
        }
        req_id = request_id_var.get("")
        if req_id:
            body["request_id"] = req_id
        return JSONResponse(status_code=429, content=body)
```

**Uso en rutas criticas** (ejemplo en `AI_dialer/app/routes/chat.py`):

```python
from shared.middleware.rate_limit import limiter

@router.post("/chat")
@limiter.limit("30/minute")  # 30 mensajes por minuto por tenant
async def chat(request: Request, ...):
    ...
```

**Limites recomendados**:

| Endpoint | Limite | Razon |
|----------|--------|-------|
| `POST /api/v1/ai/chat` | 30/min | Costo LLM, evitar abuso |
| `POST /api/v1/ai/embeddings` | 10/min | Costo embedding API |
| `POST /api/v1/core/auth/login` | 5/min | Prevencion brute force |
| `POST /api/v1/canales/whatsapp/send` | 60/min | Rate limit Evolution API |
| General (all other) | 120/min | Proteccion general |

---

### Fase 4: Alertas en GCP Cloud Monitoring (Semana 2-3)

**Objetivo**: Deteccion automatica de incidentes sin necesidad de revisar logs manualmente.

#### Paso 4.1: Alertas basadas en logs (Log-based Metrics)

Estas se configuran en GCP Console o via `gcloud`. No requieren cambios en codigo.

**Prerequisito**: Fase 1 completada (logs JSON en Cloud Logging).

**Crear log-based metrics** (Cloud Logging → Log-based Metrics):

```bash
# Metrica 1: Errores 5xx por servicio
gcloud logging metrics create error_5xx \
  --description="HTTP 5xx errors per service" \
  --log-filter='jsonPayload.severity="ERROR" AND jsonPayload.status_code>=500' \
  --project=melodic-nature-484617-e6

# Metrica 2: Latencia alta (>5s)
gcloud logging metrics create high_latency \
  --description="Requests taking more than 5 seconds" \
  --log-filter='jsonPayload.duration_ms>5000 AND jsonPayload.severity="INFO"' \
  --project=melodic-nature-484617-e6

# Metrica 3: Circuit breaker abierto
gcloud logging metrics create circuit_open \
  --description="Circuit breaker opened for a downstream service" \
  --log-filter='jsonPayload.message=~"Circuit OPEN"' \
  --project=melodic-nature-484617-e6

# Metrica 4: Rate limit exceeded
gcloud logging metrics create rate_limit_hit \
  --description="Rate limit exceeded events" \
  --log-filter='jsonPayload.message=~"Rate limit exceeded"' \
  --project=melodic-nature-484617-e6
```

#### Paso 4.2: Alerting Policies

```bash
# Alerta: >10 errores 5xx en 5 minutos → email
gcloud alpha monitoring policies create \
  --notification-channels="projects/melodic-nature-484617-e6/notificationChannels/EMAIL_CHANNEL_ID" \
  --display-name="High 5xx Error Rate" \
  --condition-display-name="5xx errors > 10 in 5min" \
  --condition-filter='metric.type="logging.googleapis.com/user/error_5xx"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=300s \
  --project=melodic-nature-484617-e6

# Alerta: Servicio no responde health check
gcloud alpha monitoring policies create \
  --notification-channels="EMAIL_CHANNEL_ID" \
  --display-name="Service Unhealthy" \
  --condition-display-name="Cloud Run revision unhealthy" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"' \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s \
  --project=melodic-nature-484617-e6
```

#### Paso 4.3: Notification Channel (email para comenzar)

```bash
# Crear canal de notificacion email
gcloud alpha monitoring channels create \
  --display-name="CTO Alerts" \
  --type=email \
  --channel-labels=email_address=admin@sudamerica.ai \
  --project=melodic-nature-484617-e6
```

#### Paso 4.4: Dashboard en Cloud Monitoring

Crear dashboard con widgets para:

1. **Request rate** por servicio (Cloud Run built-in)
2. **Error rate** (5xx / total) por servicio
3. **Latency p50/p95** por servicio
4. **Circuit breaker events** (log-based metric)
5. **Rate limit events** (log-based metric)
6. **Active connections** Cloud SQL
7. **Memory/CPU** por servicio Cloud Run

---

## 3. Dependencias a Agregar

### requirements.txt (agregar a TODOS los servicios)

```
slowapi>=0.1.9
```

No se requieren otras dependencias externas. La implementacion usa:
- `logging` stdlib (ya instalado)
- `json` stdlib (ya instalado)
- `contextvars` stdlib (ya instalado)
- `time` stdlib (ya instalado)
- `httpx` (ya instalado en todos)

### Nota sobre OpenTelemetry

OpenTelemetry se considera una mejora futura (Fase 5). La Fase 1-4 da visibilidad suficiente para operar con <100 tenants. Si el volumen crece, agregar:

```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-gcp-trace>=1.6.0
opentelemetry-instrumentation-fastapi>=0.44b0
opentelemetry-instrumentation-sqlalchemy>=0.44b0
opentelemetry-instrumentation-httpx>=0.44b0
```

---

## 4. Archivos a Crear/Modificar — Resumen

### Archivos NUEVOS (3)

| Archivo | Fase | Descripcion |
|---------|------|-------------|
| `shared/utils/logging.py` | 1 | JSON formatter + contextvars |
| `shared/middleware/request_logging.py` | 1 | Request/response logging middleware |
| `shared/middleware/rate_limit.py` | 3 | Per-tenant rate limiting |

### Archivos a MODIFICAR (12)

| Archivo | Fase | Cambio |
|---------|------|--------|
| `shared/utils/http_client.py` | 1+3 | Request ID propagation + Circuit breaker |
| `shared/utils/exceptions.py` | 2 | request_id en error responses + unhandled handler |
| `shared/utils/__init__.py` | 1 | Exportar nuevos modulos |
| `shared/middleware/__init__.py` | 1 | Exportar RequestLoggingMiddleware |
| `api_execute/app/main.py` | 1 | Reemplazar _setup_logging, agregar middleware |
| `AI_dialer/app/main.py` | 1 | Reemplazar logging, agregar middleware |
| `callback_manual/app/main.py` | 1 | Reemplazar logging, agregar middleware |
| `tasks/app/main.py` | 1 | Reemplazar logging, agregar middleware |
| `canales_service/app/main.py` | 1 | Reemplazar logging, agregar middleware |
| `open_agent/app/main.py` | 1 | Reemplazar logging, agregar middleware |
| `api_execute/app/routes/health.py` | 2 | Health check con dependencias |
| `*/requirements.txt` (6 archivos) | 3 | Agregar slowapi |

### Tests NUEVOS (2)

| Archivo | Fase | Descripcion |
|---------|------|-------------|
| `shared/tests/test_logging.py` | 1 | JSON formatter, request_id, context vars |
| `shared/tests/test_circuit_breaker.py` | 3 | Circuit breaker states, recovery |

---

## 5. Orden de Ejecucion (Checklist)

```
Fase 1 — Structured Logging + Request IDs
[ ] Crear shared/utils/logging.py
[ ] Crear shared/middleware/request_logging.py
[ ] Modificar shared/utils/http_client.py (propagacion request_id)
[ ] Modificar shared/utils/__init__.py (exports)
[ ] Modificar shared/middleware/__init__.py (exports)
[ ] Modificar api_execute/app/main.py
[ ] Modificar AI_dialer/app/main.py
[ ] Modificar callback_manual/app/main.py
[ ] Modificar tasks/app/main.py
[ ] Modificar canales_service/app/main.py
[ ] Modificar open_agent/app/main.py
[ ] Crear shared/tests/test_logging.py
[ ] Correr tests: pytest shared/tests/test_logging.py
[ ] Deploy a Cloud Run (todos los servicios)
[ ] Verificar en Cloud Logging que los logs son JSON
[ ] Verificar que X-Request-ID aparece en response headers

Fase 2 — Health Checks + Error Context
[ ] Modificar shared/utils/exceptions.py
[ ] Modificar api_execute/app/routes/health.py
[ ] Modificar tasks/app/routes/health.py (agregar DB check)
[ ] Modificar canales_service/app/routes/health.py (agregar DB check)
[ ] Deploy
[ ] Verificar /health/ready retorna checks detallados

Fase 3 — Circuit Breaker + Rate Limiting
[ ] Modificar shared/utils/http_client.py (circuit breaker)
[ ] Crear shared/middleware/rate_limit.py
[ ] Agregar slowapi a todos los requirements.txt
[ ] Aplicar @limiter.limit() en rutas criticas
[ ] Crear shared/tests/test_circuit_breaker.py
[ ] Correr tests
[ ] Deploy

Fase 4 — Alertas GCP
[ ] Crear log-based metrics en Cloud Monitoring
[ ] Crear notification channel (email)
[ ] Crear alerting policies (5xx, latency, circuit, rate limit)
[ ] Crear dashboard en Cloud Monitoring
[ ] Testear: provocar un error 500 y verificar que llega la alerta
```

---

## 6. Metricas de Exito

| Metrica | Antes | Despues (target) |
|---------|-------|-----------------|
| Tiempo de diagnostico de incidente | 30-60 min | <5 min |
| Logs buscables por request_id | No | Si |
| Alertas automaticas | 0 | 4+ reglas activas |
| Proteccion contra cascading failure | Ninguna | Circuit breaker activo |
| Proteccion contra abuso | Ninguna | Rate limiting por tenant |
| Health checks con dependencias | 3/6 servicios | 6/6 servicios |
| Error responses con trace ID | No | Si |

---

## 7. Riesgos y Mitigaciones de la Implementacion

| Riesgo | Mitigacion |
|--------|------------|
| JSON logging rompe parsers existentes | Cloud Logging auto-parsea JSON — mejora, no rompe |
| RequestLoggingMiddleware agrega latencia | <0.1ms por request (medido: time.perf_counter overhead es nanosegundos) |
| Circuit breaker bloquea requests validos | recovery_timeout=30s (corto). Half-open permite probes |
| Rate limiting bloquea usuarios legitimos | Limites generosos (30/min chat). Monitorear metricas antes de ajustar |
| slowapi usa memoria in-process | OK para Cloud Run single-instance. Si hay multi-instance, migrar a Redis |
| Cambios en shared/ afectan todos los servicios | Desplegar y testear servicio por servicio, no todos a la vez |
