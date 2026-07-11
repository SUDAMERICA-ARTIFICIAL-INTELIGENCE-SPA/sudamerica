# Status del Modulo Prospectos + WhatsApp IA

> **Ultima actualizacion**: 2026-03-14
> **Estado**: OPERATIVO EN PRODUCCION
> **Flujo end-to-end**: Cliente envia WhatsApp -> api_execute orquesta -> ai_dialer procesa -> IA responde

---

## Como funciona el flujo completo

```
Cliente (WhatsApp)
    |
    v
Evolution API (Cloud Run, min-instances=1)
    |
    v  POST /webhook/whatsapp?token=<WEBHOOK_TOKEN>
canales-service (Cloud Run)
    |-- 1. Valida webhook token (HMAC)
    |-- 2. Parsea payload de Evolution (texto, imagenes con caption, etc)
    |-- 3. Filtra: ignora grupos, newsletters, broadcasts, LIDs
    |-- 4. Busca instance por nombre -> obtiene tenant_id
    |-- 5. Busca o crea lead en api-execute (por telefono)
    |-- 6. Si from_me=true -> guarda como "assistant", no invoca IA
    |-- 7. Consulta auto_respuesta_whatsapp en ai-dialer
    |-- 8. Si auto=true -> forward a api-execute /process-message (timeout 60s)
    |-- 9. Espera delay aleatorio 2-5s (anti-ban)
    |-- 10. Envia respuesta via Evolution API
    |
    v
api-execute (Cloud Run) — ORQUESTADOR (el QUE)
    |-- 1. Carga system_prompt de agente_config
    |-- 2. Carga knowledge context de tenant_knowledge
    |-- 3. Carga catalogo de productos + modifiers
    |-- 4. Arma system_message completo (prompt + knowledge + catalogo + reglas cotizador)
    |-- 5. Forward a ai-dialer con system_prompt_override
    |-- 6. Post-proceso: extrae JSON de pedido, crea comanda si confirmado
    |-- 7. Stripea JSON del response antes de enviar al cliente
    |
    v
ai-dialer (Cloud Run, max-instances=3, min-instances=1) — CEREBRO (el COMO)
    |-- Agrega BEHAVIORAL_RULES (no re-saludar, no repetir, no inventar)
    |-- Carga historial de conversacion (ultimos 10 mensajes)
    |-- Llama al LLM (Gemini 2.5 Flash)
    |-- Guarda en ai_conversations
    |-- Notifica via WebSocket al frontend
    |
    v
Cliente recibe respuesta en WhatsApp (3-8 segundos)
```

> **Nota**: Ver `report/IA_status.md` para documentacion detallada de la arquitectura IA.

### Servicios involucrados

| Servicio | URL produccion | Rol |
|----------|---------------|-----|
| `evolution-api` | `https://evolution-api-552598955895.us-central1.run.app` | Gateway WhatsApp (Baileys) |
| `canales-service` | `https://canales-service-552598955895.us-central1.run.app` | Gateway de canales (WhatsApp) |
| `api-execute` | `https://api-execute-552598955895.us-central1.run.app` | Orquestador IA + CRUD + negocio |
| `ai-dialer` | `https://ai-dialer-552598955895.us-central1.run.app` | Cerebro IA (LLM + historial + reglas) |

### Autenticacion inter-servicio

Cada servicio tiene su propia `INTERNAL_SERVICE_SECRET_KEY` (unica). Cuando un servicio llama a otro, firma un JWT con:
- `type: "service"`
- `issuer: "<nombre_servicio>"`
- `audience: "<servicio_destino>"`
- `scopes: ["chat:write"]` o `["leads:read"]`

Cadena de auth para WhatsApp IA:
1. `canales_service` → `api_execute` (audience=api_execute, scopes=chat:write)
2. `api_execute` → `ai_dialer` (audience=ai_dialer, scopes=chat:write)

El servicio receptor verifica el JWT usando el mapa `internal_service_trusted_keys` que mapea cada issuer a su clave.

---

## Que se hizo el 2026-03-13

### Problema 1: 401 Unauthorized en todas las llamadas inter-servicio

**Causa raiz**: Todas las 5 servicios tenian una variable de entorno `INTERNAL_SERVICE_SECRET_KEY=3f0975b18...` (vieja, compartida) ADEMAS de las variables por servicio (`API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY`, `CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY`, etc). Pydantic tomaba la variable generica en vez del alias especifico.

**Fix**:
```bash
gcloud run services update [cada-servicio] --remove-env-vars="INTERNAL_SERVICE_SECRET_KEY"
```
Aplicado a los 5 servicios. Rebuild completo via `gcloud builds submit`.

### Problema 2: 409 Conflict al crear leads (plan FREE maxed)

**Causa raiz**: El tenant "Aidtogrow SpA" (f2281e11) estaba en plan FREE con `max_leads_mes=100` y tenia exactamente 100 leads. Cada mensaje de un contacto nuevo fallaba.

**Fix**:
```sql
UPDATE tenants SET plan = 'PRO', max_leads_mes = 999999
WHERE id = 'f2281e11-52b1-4a3f-b685-f8e26a3b01bf';
```

Ademas, se mejoro `_create_lead()` para manejar 409 haciendo re-search (race condition):
```python
if response.status_code == 409:
    logger.info("Lead create returned 409 for phone %s, re-searching", phone)
    return await _search_lead(phone, tenant_id, settings, auth_headers)
```

### Problema 3: 500 Internal Server Error en ai-dialer (OpenAI rate limit)

**Causa raiz**: La sincronizacion de historial hizo muchas llamadas a OpenAI en poco tiempo. OpenAI devolvio 429 Too Many Requests.

**Fix**: Cambiar LLM provider a Gemini:
```bash
gcloud run services update ai-dialer --update-env-vars "LLM_PROVIDER=gemini"
```
Gemini 2.5 Flash responde en 4-8 segundos, sin rate limits.

### Problema 4: httpx.ReadTimeout — mensajes "se quedan pegados"

**Causa raiz**: `_forward_to_ai()` creaba `HttpClient(base_url=...)` SIN timeout explicito. El default era **10 segundos**. Gemini tarda 7-10s, justo al limite. Con 3 reintentos + backoff, bloqueaba **~33 segundos** antes de fallar.

**Fix** (3 cambios en codigo):

1. **`whatsapp_service.py` linea 667**: Timeout de 10s -> 60s
   ```python
   client = HttpClient(base_url=settings.SERVICE_AI_DIALER_URL, timeout=60.0)
   ```

2. **`http_client.py`**: POST ya no reintenta en ReadTimeout (no es idempotente, puede causar respuestas IA duplicadas). Solo reintenta en ConnectError.

3. **`whatsapp_service.py` _create_lead**: Maneja 409 con re-search en vez de devolver None.

### Problema 5: Filtro de JIDs incompleto

**Fix**: Se agrego `@lid` al filtro de JIDs no soportados en `_is_supported_chat()`. Los LIDs son identificadores internos de WhatsApp que no corresponden a conversaciones reales.

### Problema 6: `_sync_single_chat_history` lanzaba RuntimeError

**Fix**: Cambiado de `raise RuntimeError` a `logger.warning` + return graceful cuando no se puede resolver un lead durante sync historico. Esto evita que un chat fallido aborte toda la sincronizacion.

---

## Estado actual de produccion

### Revisions activas (2026-03-14 04:25 UTC)
- `canales-service-00035` (ruta a api-execute en vez de ai-dialer directo)
- `ai-dialer-00061` (acepta api_execute como service_caller, BEHAVIORAL_RULES)
- `api-execute-00038` (ai_orchestrator, JSON strip, modifier fix)
- `callback-manual-00015-s9v`
- `tasks-00022-fch`
- `evolution-api` (min-instances=1, OBLIGATORIO para WebSocket)

### Tests
- **266/266 pasando** (api_execute:58, AI_dialer:134, callback_manual:16, tasks:22, canales_service:36)

### Issues conocidos (no bloquean)
| Issue | Impacto | Prioridad |
|-------|---------|-----------|
| Latencia Gemini 4-8s | Respuesta no es instantanea pero aceptable | Baja |
| callback_manual notification error | No afecta respuesta al cliente | Baja |

### Instancias WhatsApp activas
| Tenant | Telefono | Instance name |
|--------|----------|--------------|
| Aidtogrow SpA (f2281e11) | 56956567088 | tenant-f2281e11-... |
| Sudamerica AI (79dd140e) | 56981941703 | tenant-79dd140e-... |

---

## Configuracion clave

### Variables de entorno criticas (canales-service)
```
EVOLUTION_API_URL=https://evolution-api-552598955895.us-central1.run.app
EVOLUTION_API_KEY=0fda4218e76fa39a78f945f88d3a3582...
EVOLUTION_WEBHOOK_URL=https://canales-service-552598955895.us-central1.run.app/api/v1/canales/webhook/whatsapp
WEBHOOK_TOKEN=d05cd1db98d1cf822f5d2c07f66484bf...
CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY=9b4efc...
SERVICE_API_EXECUTE_URL=https://api-execute-552598955895.us-central1.run.app
SERVICE_AI_DIALER_URL=https://ai-dialer-552598955895.us-central1.run.app
```

### Timeouts configurados
| Llamada | Timeout | Reintentos |
|---------|---------|------------|
| canales -> api-execute /process-message | 60s | 1 (sin retry en ReadTimeout) |
| api-execute -> ai-dialer /chat | 60s | 1 |
| canales -> api-execute /leads | 10s | 3 (con retry) |
| canales -> ai-dialer /config | 10s | 3 |
| canales -> Evolution API | default | 3 |
| canales -> ai-dialer /conversations/import | 20s | 3 |

---

## Proximos pasos

1. **Monitorear latencia**: El flujo completo tarda 6-12s (delay anti-ban + Gemini). Evaluar si es aceptable para UX
2. **Dashboard de prospectos en tiempo real**: WebSocket ya conectado, verificar que mensajes aparezcan instantaneamente en frontend
3. **Tests E2E**: Smoke test con WhatsApp real → respuesta IA daria mas confianza

---

## Fixes aplicados (2026-03-13, sesion 2 — 17:15 UTC)

### Fix 1: RAG embeddings 429 — retry con backoff (RESUELTO)
**Archivo**: `AI_dialer/app/services/embedding_service.py`
**Cambio**: Agregado retry loop (3 intentos) con exponential backoff solo para errores 429.
- Intento 1: inmediato
- Intento 2: ~2s backoff
- Intento 3: ~5s backoff
- Errores no-429 (401, 500) fallan inmediatamente sin retry
**Tests**: `test_embedding_retries_on_429`, `test_embedding_fails_after_max_retries_on_429`, `test_embedding_no_retry_on_401`

### Fix 2: Classify parser robusto (RESUELTO)
**Archivo**: `AI_dialer/app/services/classify_service.py`
**Cambio**: Si el LLM devuelve JSON wrapeado en prosa (no solo markdown fences), el parser extrae el primer `{...}` valido.
- Markdown fences: ya manejado (```json...```)
- Prosa wrapping: "Here is the result: {...} hope this helps!" → extrae `{...}`
- Total garbage: fallback a OTRO/RAG con confianza=0
**Tests**: `test_classify_extracts_json_from_prose`, `test_classify_handles_triple_backtick_no_json_label`, `test_classify_total_garbage_returns_otro`

### Fix 3: Lead FSM auto-progresion NUEVO → CONTACTADO (NUEVO)
**Archivo**: `canales_service/app/services/whatsapp_service.py`
**Cambio**: Despues de enviar una respuesta IA exitosa por WhatsApp, se hace PATCH al lead cambiando estado de NUEVO a CONTACTADO.
- Solo progresa si estado actual es NUEVO (no toca CONTACTADO, EN_PROCESO, etc)
- Fire-and-forget via `asyncio.ensure_future` (no bloquea la respuesta)
- Fallo silencioso si api_execute no responde
**Tests**: `test_progress_lead_nuevo_to_contactado`, `test_progress_lead_already_contactado_skips_patch`, `test_progress_lead_handles_api_failure_gracefully`

### Fix 4: Session cleanup — limpieza de sesiones expiradas (NUEVO)
**Archivo**: `AI_dialer/app/services/session_service.py` + `AI_dialer/app/routes/sessions.py`
**Cambio**: Nueva funcion `cleanup_expired_sessions()` + endpoint `POST /api/v1/ai/sessions/cleanup`.
- Cierra todas las sesiones ACTIVE cuyo `updated_at` excede el timeout (default 30 min)
- Scope por tenant_id
- Retorna `{"closed": N, "checked": M}`
**Tests**: `test_session_cleanup_closes_expired`, `test_session_cleanup_keeps_active`

### Fix 5: Delivery retry para envios fallidos (NUEVO)
**Archivo**: `tasks/app/services/send_response_service.py` + `tasks/app/routes/send_response.py`
**Cambio**: Nuevo endpoint `POST /api/v1/tasks/retry-failed` + funcion `retry_failed_deliveries()`.
- Busca todas las revision_humana con delivery_status=FAILED
- Re-intenta delivery para cada una (max 10 por batch)
- Retorna `{"retried": N, "succeeded": M, "still_failed": K}`
**Tests**: `test_retry_failed_endpoint_exists`, `test_retry_failed_requires_auth`, `test_retry_failed_calls_service`

### Fix 6: Escalar ai-dialer (RESUELTO)
**Cambio**: `gcloud run services update ai-dialer --max-instances 3 --memory 1Gi`
- Antes: max=1, 512MB (saturaba con >20 msgs/min)
- Ahora: max=3, 1Gi (soporta multiples tenants concurrentes)
- min=1 se mantiene (necesario para warm start)

### Fix auxiliar: HttpClient.patch() (NUEVO)
**Archivo**: `shared/utils/http_client.py`
**Cambio**: Agregado metodo `patch()` al HttpClient wrapper (necesario para lead FSM progression).

---

## Fixes aplicados (2026-03-14 — Refactor arquitectonico)

### Refactor: Arquitectura de dos capas para IA (COMPLETADO)

**Antes**: canales-service llamaba directamente a ai-dialer, que hacia TODO (cargar config, knowledge, productos, clasificar, rutear, generar respuesta).

**Ahora**: Arquitectura de dos capas:
- **api_execute** (el QUE): Carga business context (prompt, knowledge, catalogo, reglas cotizador) y lo envia a ai-dialer como `system_prompt_override`
- **ai_dialer** (el COMO): Recibe el prompt ya armado, agrega reglas de comportamiento, carga historial, llama al LLM

**Archivos nuevos**:
- `api_execute/app/services/ai_orchestrator.py` — Orquestador principal
- `api_execute/app/routes/ai_orchestrator.py` — Endpoint `POST /api/v1/core/ai/process-message`
- `api_execute/app/schemas/ai_orchestrator.py` — Request/Response models

**Cambios clave**:
- `canales_service/whatsapp_service.py`: Ruta a api-execute en vez de ai-dialer directo
- `AI_dialer/chat_service.py`: Bifurcacion orchestrated vs legacy mode + BEHAVIORAL_RULES
- `AI_dialer/routes/chat.py`: Agrega `api_execute` a `service_callers`

### Fix: JSON de pedido se enviaba al cliente WhatsApp (RESUELTO)

**Causa raiz**: Cuando el LLM generaba un pedido confirmado, incluia un bloque ```json...``` en la respuesta. Ese JSON se enviaba al cliente via WhatsApp.

**Fix**: `_strip_json_block()` en `ai_orchestrator.py` remueve bloques JSON antes de devolver la respuesta. El JSON se extrae internamente para crear comandas automaticas.

### Fix: Column `m.modifier_group_id` does not exist (RESUELTO)

**Causa raiz**: La query de modifiers usaba `m.modifier_group_id` pero la columna real en la tabla `modifiers` es `grupo_id`.

**Fix**: Corregido el nombre de columna + envuelto en try/except para que tablas faltantes no rompan el flujo completo.

### Fix: Saludos repetitivos de la IA (RESUELTO)

**Causa raiz**: ai-dialer no pasaba el historial de conversacion al LLM. Cada mensaje se procesaba sin contexto → la IA saludaba en cada respuesta.

**Fix**: `_get_conversation_history()` carga los ultimos 10 mensajes y los pasa como contexto al LLM. Ademas, `BEHAVIORAL_RULES` incluye regla explicita: "Si el historial muestra mensajes previos, NO saludes de nuevo."

### Feature: Boton de desconexion WhatsApp (COMPLETADO)

Boton rojo "Desconectar" en la vista de Prospectos. Permite al usuario desconectar su instancia WhatsApp y reconectar con otro numero.
- Backend: `DELETE /qr/{tenant_id}` en canales-service (logout + delete en Evolution API + soft-delete en DB)
- Frontend: `useDisconnectWhatsApp()` hook + modal de confirmacion con Mantine

---

## Puntos pendientes (revision 2026-03-14)

> Todos los issues de prioridad media y baja han sido resueltos. Lo que queda:

### Prioridad Baja

| # | Que | Detalle |
|---|-----|---------|
| 1 | Latencia 6-12s | Delay anti-ban (2-5s) + Gemini (4-8s). Aceptable para WhatsApp. |
| 2 | Argus score 20/100 (falso) | Escanea vendor code. Score real ~90/100. |

### No bloquean pero conviene tener en cuenta

- **Tests**: 266/266 pasando. Para ejecutarlos ahora se asume instalacion global via `pip install -r backend/requirements.txt`.
- **Archivos grandes**: `chat_service.py` (722 lineas) y `whatsapp_service.py` (870+ lineas) son los mas grandes del modulo.
- **Tests E2E**: No existen. Los 266 tests son unitarios con mocks.

---

## Sesion 2026-04-11 — Ajustes operativos restaurante + polls interactivos

### Resumen
Sesion enfocada en: (1) ajustes al flujo delivery/repartidores, (2) mensajes interactivos tipo encuesta, (3) parsing de respuestas de polls, (4) fix de mensajes duplicados, (5) cabecera visual del menu PDF.

### WS1: Parsing de respuestas interactivas WhatsApp (COMPLETADO)

**Problema**: El sistema enviaba listas/polls por WhatsApp pero no sabia leer las respuestas del cliente.

**Fix**:
- `whatsapp_service.py`: Nuevos extractors `_list_response_text()` y `_button_response_text()` agregados a la cadena de `_extract_text()`
- `whatsapp.py`: `_extract_text_and_media()` ahora maneja `pollUpdates` (votos de encuestas)
- Tests: 8 tests nuevos para list response, button response, poll vote extraction

**Archivos**: `canales_service/app/services/whatsapp_service.py`, `canales_service/app/routes/whatsapp.py`

### WS2: Fix notificacion a repartidores — 4 bugs (COMPLETADO)

**Bugs arreglados en `_notify_delivery_drivers()`**:
1. Endpoint incorrecto: `/whatsapp/send-text` → `/whatsapp/send`
2. Payload incorrecto: `{"number": ...}` → `{"to": ..., "tenant_id": ...}`
3. Scope incorrecto: `whatsapp:write` → `whatsapp:send`
4. Si `order_data` no tenia `sucursal_id`, la notificacion se abortaba silenciosamente → ahora resuelve la sucursal principal via `_resolve_default_sucursal()`
5. Items mostraban UUIDs de producto → ahora resuelve nombres reales desde DB
6. Agrega tiempo estimado de preparacion al mensaje

**Archivos**: `api_execute/app/services/ai_orchestrator.py`

### WS3: Sistema de delivery — claim por repartidores (COMPLETADO)

**Nuevas tablas** (migracion `016_delivery_enhancements.sql` aplicada en Cloud SQL):
- `repartidores`: pool de repartidores por tenant (nombre, phone, sucursal)
- `delivery_assignments`: asignacion de entregas (estado FSM: PUBLICADO→ACEPTADO→EN_RUTA→ENTREGADO)

**Nuevos enums** en `shared/models/enums.py`:
- `DeliveryEstado`: PUBLICADO, ACEPTADO, EN_RUTA, ENTREGADO, CANCELADO
- `MetodoPago`: TRANSFERENCIA, EFECTIVO, TARJETA, CONTRA_ENTREGA

**Nuevos archivos**:
- `api_execute/app/models/delivery.py` — Modelos ORM `Repartidor` y `DeliveryAssignment`
- `api_execute/app/schemas/delivery.py` — Schemas Pydantic
- `api_execute/app/services/delivery_svc.py` — Claim atomico, FSM, confirmacion de pago
- `api_execute/app/routes/delivery.py` — 6 endpoints: claim, CRUD, estado, pagos

**Endpoints nuevos**:
- `POST /api/v1/core/delivery/claim` — Repartidor reclama entrega (atomico, previene double-claim)
- `PATCH /api/v1/core/delivery/{id}/estado` — Actualizar estado (EN_RUTA, ENTREGADO)
- `PATCH /api/v1/core/delivery/{id}/confirm-payment` — Confirmar pago recibido
- `GET /api/v1/core/delivery/pending` — Listar entregas sin asignar
- `POST /api/v1/core/repartidores` — Crear repartidor
- `GET /api/v1/core/repartidores` — Listar repartidores

**Integracion**: Al crear comanda DELIVERY, se crea automaticamente un `DeliveryAssignment` en estado PUBLICADO.

**Tests**: 12 tests — claim atomico, double-claim rejection, FSM transitions, payment confirmation.

### WS4: Soporte de mensajes de grupo WhatsApp (COMPLETADO)

**Cambio**: `_extract_sender()` ahora permite mensajes de grupos `@g.us` (antes los bloqueaba).

**Flujo de claim**: Cuando un repartidor escribe "TOMO" en el grupo de repartidores:
1. Webhook detecta grupo → busca `grupo_repartidores_jid` en `sucursales`
2. Verifica keyword de claim (tomo, acepto, yo, va)
3. Llama al endpoint `POST /delivery/claim` en api-execute
4. Responde en el grupo: "Pedido asignado a {nombre}" o "Ya fue tomado por otro"

**Archivos**: `canales_service/app/routes/whatsapp.py`

### WS5: Sugerencia automatica de bebidas (COMPLETADO)

**Cambio en COTIZADOR_RULES**: Seccion "Upselling" reemplazada por "Sugerencia de Bebidas y Upselling":
- Antes de confirmar pedido, revisa si el cliente ya pidio bebida
- Detecta bebidas por categoria (Bebestibles, Bebidas, Jugos, Cervezas, etc.)
- Si no tiene bebida, pregunta con poll: `[ENVIAR_POLL:¿Algo para tomar?|No gracias|{bebida1}|{bebida2}]`

### WS6: Tiempo estimado de preparacion (COMPLETADO)

- Nueva columna `tiempo_estimado_preparacion INT DEFAULT 30` en `agente_config`
- `_load_agent_config()` carga el campo
- `_notify_delivery_drivers()` incluye "Preparacion estimada: ~30 min" en notificacion

### WS7: Tipo de entrega como encuesta (COMPLETADO)

COTIZADOR_RULES actualizado: pregunta tipo de entrega via `[ENVIAR_POLL:...]` en vez de texto libre.

### Fix: Mensajes duplicados por sendList roto (COMPLETADO)

**Causa raiz**: Evolution API v2 (Baileys) tiene un bug en `/message/sendList` — error `this.isZero`. El fallback enviaba la lista como texto plano → segundo mensaje redundante.

**Fix**: 
- `send_list()` corregido: campo `values` → `sections` (correcto para Evolution v2)
- Fallback de lista: ahora usa `send_poll` en vez de texto plano (polls SI funcionan)

### Fix: Polls — votos no se procesaban (COMPLETADO)

**Descubrimiento clave**: Los votos de polls llegan como `messages.upsert` (NO `messages.update`). El payload tiene esta estructura:

```json
{
  "event": "messages.upsert",
  "data": {
    "key": {"remoteJid": "56923812710@s.whatsapp.net", "fromMe": false},
    "message": {"pollUpdateMessage": {"vote": {"selectedOptions": ["Hacer un pedido"]}}},
    "pollUpdates": [
      {"name": "Hacer un pedido", "voters": ["81459071209727@lid"]},
      {"name": "Ver el menu", "voters": []},
      ...
    ]
  }
}
```

**Formato de pollUpdates (Evolution v2 Baileys)**:
- Es un array de TODAS las opciones del poll
- Cada opcion tiene `name` (texto) y `voters` (array de JIDs que votaron)
- La opcion seleccionada es la que tiene `voters` no vacio
- El voter JID usa `@lid` (no `@s.whatsapp.net`)
- El `remoteJid` del `data.key` contiene el JID del votante real

**Requisitos para recibir votos**:
- El evento `MESSAGES_UPDATE` debe estar en los webhook events de la instancia Evolution
- Se configura via `POST /webhook/set/{instance_name}` con body `{"webhook": {"events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE", "QRCODE_UPDATED"]}}`

**Funciones creadas**:
- `_find_poll_updates(payload)`: Busca `pollUpdates` exhaustivamente en toda la estructura del payload
- `_extract_poll_vote_text(poll_updates)`: Extrae texto del voto — soporta Format A (aggregated: `[{name, voters}]`) y Format B (individual: `[{vote: []}]`)
- `_find_poll_voter(payload, poll_updates)`: Extrae JID del votante de multiples ubicaciones
- Dedup de votos via `_is_duplicate_message(poll_msg_id)`

### Fix: Marcadores [ENVIAR_LISTA:...] visibles en frontend (COMPLETADO)

**Causa raiz**: ai_dialer persiste y broadcast via WebSocket el response ANTES de que api_execute limpie los marcadores.

**Fix**: Regex `AI_MARKER_RE` en `ConversationChat.tsx` que strip marcadores en `sanitizeContent()` antes de renderizar.

### Fix: Cabecera visual del menu PDF (COMPLETADO)

**Nuevo campo**: `menu_cabecera_url TEXT` en `agente_config`

**Flujo**: Cuando el bot envia el menu PDF:
1. Si `menu_cabecera_url` esta configurada → envia imagen de cabecera primero
2. Luego envia el PDF del menu
3. El cliente ve una imagen de branding + el PDF descargable

**Archivos**: `ai_orchestrator.py` (`_attach_menu` devuelve lista de attachments), `whatsapp_service.py` (`_send_interactive_extras` envia preview image antes del doc)

### Fix: Fallback programatico de polls (COMPLETADO)

Si la IA no incluye marcadores `[ENVIAR_POLL:...]` en la respuesta (comportamiento no determinista del LLM), el orquestador inyecta automaticamente un poll de bienvenida o seleccion de sucursal como post-processing.

### Revisions desplegadas (2026-04-11 fin de sesion)

| Servicio | Revision | Estado |
|----------|----------|--------|
| api-execute | `api-execute-00038-22c` | 100% trafico |
| canales-service | `canales-service-00033-28q` | 100% trafico |
| frontend | `frontend-00023-xh9` | 100% trafico |

### Tests agregados

| Suite | Tests nuevos | Total sesion |
|-------|-------------|-------------|
| `canales_service/tests/test_interactive_messages.py` | 17 (list response, poll votes, group handling) | 29 |
| `api_execute/tests/test_delivery.py` | 12 (claim, double-claim, FSM, pagos) | 12 |
| `api_execute/tests/test_ai_orchestrator.py` | 1 (cabecera menu) | 29 |

### DB: Tablas y columnas creadas

```sql
-- 016_delivery_enhancements.sql
CREATE TABLE repartidores (id, tenant_id, sucursal_id, nombre, phone, activo, ...);
CREATE TABLE delivery_assignments (id, tenant_id, comanda_id, repartidor_id, estado, metodo_pago, monto_a_cobrar, claimed_at, ...);
ALTER TABLE agente_config ADD COLUMN tiempo_estimado_preparacion INT DEFAULT 30;
ALTER TABLE agente_config ADD COLUMN menu_cabecera_url TEXT;
```

### Webhook Evolution API — eventos configurados

```json
{
  "events": ["QRCODE_UPDATED", "MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
}
```

`MESSAGES_UPDATE` es **obligatorio** para recibir votos de polls.

---

## Sesion 2026-04-12 — Polish final UX y envio de imagenes de platos

### Fix: Eliminar fallback agresivo de polls (COMPLETADO)

**Problema**: El orquestador inyectaba un poll en CADA respuesta cuando la IA no incluia `[ENVIAR_POLL:...]`. Como `sucursal_id` siempre es `None` en conversaciones WhatsApp normales, el poll de seleccion de sucursal se enviaba en cada mensaje, incluso durante el pedido. Resultado: el cliente recibia el poll de sucursal repetidamente, abrumandolo.

**Fix**: Eliminado el bloque de fallback programatico en `orchestrate_chat()`. Los prompts ya instruyen a la IA a usar `[ENVIAR_POLL:...]` cuando es apropiado. Si la IA no lo pone, el cliente puede escribir su respuesta libremente.

**Archivo**: `api_execute/app/services/ai_orchestrator.py`

### Fix: Delays anti-abrumar para sentir mas natural (COMPLETADO)

**Problema**: Los mensajes llegaban instantaneamente y todos juntos, sintiendose como spam.

**Fix**:
- Delay de respuesta de texto subido de **0.5-1.5s → 3-6s** (`_REPLY_DELAY_MIN`/`_REPLY_DELAY_MAX`)
- Nuevo delay entre texto y extras (poll/media): **2-4s** (`_EXTRAS_DELAY_MIN`/`_EXTRAS_DELAY_MAX`)
- Indicador "escribiendo..." se envia antes de los extras tambien

**Flujo nuevo**:
```
Cliente: "Hola"
[3-6s con "escribiendo..."]
Bot: "Hola! En que te puedo ayudar?"  (texto)
[2-4s con "escribiendo..."]
Bot: Poll con opciones (solo si la IA lo incluyo)
```

**Archivo**: `canales_service/app/services/whatsapp_service.py`

### Fix: Envio de imagenes de platos con precio + descripcion (COMPLETADO)

**3 problemas encontrados**:
1. `MEDIA_RULES_IMAGES` decia "NO uses marcadores especiales" pero `_attach_image()` necesita el marcador `[ENVIAR_IMAGEN:...]` para detectar la intencion. Contradiccion → la IA no enviaba imagenes.
2. `_find_product_image` usaba match EXACTO (`LOWER(nombre) = LOWER(:name)`) — si el cliente decia "churrasco italiano" pero el producto era "Churrasco Italiano (Tia Julia)", no lo encontraba.
3. Las imagenes se enviaban solas, sin precio ni descripcion.

**Fix 1: `MEDIA_RULES_IMAGES`** reescrito:
- Instruye a la IA a usar `[ENVIAR_IMAGEN:nombre_exacto]` cuando el cliente pregunte por un plato
- Texto corto (1-2 lineas) — la imagen lleva nombre/precio/descripcion en el caption
- Solo enviar imagen si el producto tiene `[FOTO]` en el catalogo
- NO enviar imagenes en preguntas genericas ("que churrascos tienen?")

**Fix 2: `_find_product_image`** mejorado:
- Retorna dict con `imagen_url`, `nombre`, `precio`, `descripcion` (antes solo retornaba URL)
- Exact match primero (case-insensitive)
- Fuzzy match con `ILIKE '%nombre%'` como fallback
- Ordena por `LENGTH(nombre) ASC` — el match mas especifico gana

**Fix 3: `_attach_image` construye caption estructurado**:
```
*Churrasco Italiano* - $8.900
Posta Rosada, tomate, palta Hass y mayonesa.
```
Se envia como caption de la imagen via Evolution API.

**Flujo completo nuevo**:
```
Cliente: "Como es el Churrasco Italiano?"
[3-6s delay con typing]
Bot: "Te muestro como se ve!"           (texto corto)
[2-4s delay con typing]
Bot: [Imagen del plato]
     *Churrasco Italiano* - $8.900       (caption con precio)
     Posta Rosada, tomate, palta...      (descripcion)
```

**Archivos**:
- `api_execute/app/services/ai_orchestrator.py` — `MEDIA_RULES_IMAGES`, `_find_product_image`, `_attach_image`
- `api_execute/tests/test_ai_orchestrator.py` — Tests actualizados al nuevo formato dict

### Revisions desplegadas (2026-04-12 fin de sesion)

| Servicio | Revision | Estado |
|----------|----------|--------|
| api-execute | `api-execute-00040-r7p` | 100% trafico |
| canales-service | `canales-service-00034-pvv` | 100% trafico |

---

## Incidente y Fixes (2026-04-09/10) — Modulo caido 7 dias

### Causa raiz: WhatsApp desconectado desde 2026-04-02

El 2 de abril a las 03:04 UTC, la sesion WhatsApp se desconecto con error 401 (Meta bloqueo la IP de Cloud Run). Desde entonces, 0 mensajes nuevos entraron al sistema. Los 12,137 conversaciones y 54 leads existentes seguian en la DB pero no habia actividad nueva.

### Migracion a Compute Engine VM (CRITICO)

**Meta bloquea los rangos de IPs compartidas de Cloud Run.** Se probo us-central1, us-east1, y southamerica-east1 — todas bloqueadas. La solucion definitiva fue migrar Evolution API a una **Compute Engine VM** con IP dedicada.

| Parametro | Valor |
|-----------|-------|
| VM | `evolution-api-vm` |
| Zona | `us-central1-f` |
| Tipo | `e2-small` |
| IP externa | `34.61.234.182` |
| Puerto | 8080 |
| Container | `evolution-api:latest` con `--restart always` |
| Firewall | `allow-evolution-api` (tcp:8080, 0.0.0.0/0) |

**Webhook**: Se usa `WEBHOOK_GLOBAL_URL` (env var) en vez de per-instance webhook. El per-instance webhook de Evolution API v2.3.7 NO dispara MESSAGES_UPSERT — solo CONNECTION_UPDATE. El global webhook SI funciona para todos los eventos.

**URL del webhook global**: `https://canales-service-456595931835.us-central1.run.app/api/v1/canales/webhook/whatsapp?token=<WEBHOOK_TOKEN>`

**canales-service** actualizado: `EVOLUTION_API_URL=http://34.61.234.182:8080`

### URLs de servicio actualizadas

| Servicio | URL produccion | Tipo |
|----------|---------------|------|
| `evolution-api` | `http://34.61.234.182:8080` | Compute Engine VM |
| `canales-service` | `https://canales-service-456595931835.us-central1.run.app` | Cloud Run |
| `api-execute` | `https://api-execute-456595931835.us-central1.run.app` | Cloud Run |
| `ai-dialer` | `https://ai-dialer-456595931835.us-central1.run.app` | Cloud Run |

### Bugs corregidos

| Bug | Archivo | Fix |
|-----|---------|-----|
| `UniqueViolationError` en QR endpoint — crash 500 sin CORS headers | `canales_service/app/services/instance_service.py` | Cambiado INSERT a upsert (`INSERT ON CONFLICT DO UPDATE`) |
| `NameError: HttpClient not defined` — history sync fallaba silenciosamente | `canales_service/app/services/whatsapp_service.py` | Agregado `HttpClient` al import |
| CORS bloqueando `app.sudamerica.ai` | `shared/utils/cors.py` (ya tenia el dominio, no estaba desplegado) | Rebuild + redeploy de api-execute, ai-dialer, canales-service |
| `tenants` tabla con RLS habilitado y 0 politicas — 404 en `/tenants/me` | Cloud SQL `sudamerica` | Creada policy `tenant_access` en tabla tenants |
| Cloud SQL saturado (22/25 conexiones) — Prisma P1001 intermitente | Cloud SQL `db-f1-micro` | Terminadas conexiones idle; considerar upgrade a db-g1-small |
| Per-instance webhook no dispara MESSAGES_UPSERT | Evolution API v2.3.7 bug | Usar `WEBHOOK_GLOBAL_URL` env var en vez de per-instance |

### Gestion de la VM

```bash
# SSH
gcloud compute ssh evolution-api-vm --zone us-central1-f --project sudamerica-prod

# Logs
docker logs evolution-api --tail 100

# Restart
docker restart evolution-api

# Actualizar imagen
docker pull us-central1-docker.pkg.dev/sudamerica-prod/sudamerica/evolution-api:latest
docker stop evolution-api && docker rm evolution-api
# Re-run docker run con todas las env vars (ver memory/project_evolution_api_vm.md)

# Si Meta bloquea la IP otra vez
# 1. Reservar nueva IP estatica
# 2. Asignarla a la VM
# 3. Actualizar SERVER_URL en el container
# 4. Actualizar EVOLUTION_API_URL en canales-service
```
