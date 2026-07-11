# open_agent — Copiloto Administrativo (Sudamérica AI)

**Cerebro IA del copiloto para duenos y gerentes de restaurantes.** Este microservicio recibe instrucciones de `api_execute`, ejecuta razonamiento con herramientas (tool-calling) y retorna respuestas analiticas.

## Datos del servicio

| Campo | Valor |
|-------|-------|
| Puerto | **8005** |
| Framework | FastAPI + Uvicorn |
| Dependencia | api_execute (Orquestador) |
| Base de datos | No (stateless — sin DB propia) |
| Modelo IA | GPT-4o / Gemini 2.5 Flash (configurable) |

## Responsabilidades

- **Razonamiento Analitico**: Procesar preguntas del dueño sobre su negocio usando un modelo potente.
- **Tool-Calling**: Ejecutar herramientas que consultan/modifican datos via api_execute.
- **Aislamiento de Seguridad**: Las tools administrativas (cambiar precios, ver ingresos) SOLO existen aqui, nunca en AI_dialer.

## Pipeline de Ejecucion

1. Frontend (Sudamérica AI) envia mensaje a `api_execute POST /api/v1/core/sudamerica/chat`
2. `api_execute` construye el system prompt + contexto del tenant
3. `api_execute` reenvia a `open_agent POST /api/v1/agent/chat`
4. `open_agent` ejecuta el LLM con herramientas (loop de tool-calling)
5. Las herramientas llaman a endpoints de `api_execute` para datos reales
6. `open_agent` retorna la respuesta final a `api_execute`
7. `api_execute` persiste la conversacion y retorna al frontend

## Herramientas disponibles

| Tool | Accion | Scope requerido |
|------|--------|-----------------|
| `consultar_ventas` | Lee ventas/pedidos | ventas:read |
| `consultar_productos` | Lee menu/carta | productos:read |
| `modificar_producto` | Cambia precio/disponibilidad | productos:write |
| `consultar_clientes` | Lee clientes/leads | leads:read |
| `consultar_metricas` | Revenue, conversion, leads | metricas:read |
| `consultar_comandas` | Ordenes recientes | comandas:read |

## Endpoints

```
POST   /api/v1/agent/chat    Procesar mensaje del copiloto administrativo
GET    /health                Liveness probe
```

## Variables de entorno

- `JWT_SECRET_KEY`: Shared JWT secret
- `OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY`: Service auth key
- `API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY`: Trusted peer key
- `OPENAI_API_KEY` / `GEMINI_API_KEY`: LLM API keys
- `SERVICE_API_EXECUTE_URL`: URL de api_execute
- `LLM_PROVIDER`: `openai` o `gemini`
