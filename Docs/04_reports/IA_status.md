# Arquitectura IA — Sudamérica AI MVP

> **Ultima actualizacion**: 2026-03-14
> **Estado**: OPERATIVO EN PRODUCCION
> **Modelo activo**: Gemini 2.5 Flash (via OpenAI-compatible API)

---

## Principio de diseno: Separacion QUE vs COMO

La IA se maneja en dos capas claramente separadas:

| Capa | Servicio | Responsabilidad |
|------|----------|-----------------|
| **El QUE** (Business Context) | `api_execute` | System prompt, knowledge, catalogo productos, reglas cotizador, post-procesamiento de pedidos |
| **El COMO** (AI Engine) | `ai_dialer` | Llamadas al LLM, temperatura, historial de conversacion, reglas de comportamiento, RAG, embeddings |

**Razon**: api_execute es dueno de los datos de negocio (productos, precios, conocimiento del tenant). ai_dialer es un motor de IA generico que recibe instrucciones y las ejecuta.

---

## Flujo completo de un mensaje

```
1. Cliente envia "Quiero una pizza margarita" via WhatsApp
   |
2. canales-service recibe webhook de Evolution API
   |
3. canales-service → POST api-execute/api/v1/core/ai/process-message
   |  Payload: { message, lead_id, canal, contact_id, session_id }
   |  Auth: JWT service token (issuer=canales_service, audience=api_execute)
   |
4. api_execute: build_system_message()
   |  4a. Carga agente_config (system_prompt, modelo, temperatura)
   |  4b. Carga tenant_knowledge (FAQ, horarios, info delivery)
   |  4c. Carga catalogo productos + modifiers
   |  4d. Agrega COTIZADOR_RULES si hay productos
   |  4e. Resultado: system_message de ~2000-5000 chars
   |
5. api_execute → POST ai-dialer/api/v1/ai/chat
   |  Payload: { message, system_prompt_override, canal, lead_id, contact_id, session_id }
   |  Auth: JWT service token (issuer=api_execute, audience=ai_dialer)
   |
6. ai_dialer: chat()  [modo "orchestrated"]
   |  6a. Detecta system_prompt_override → skip clasificacion, skip sub-agentes
   |  6b. Agrega BEHAVIORAL_RULES al prompt
   |  6c. Carga historial de conversacion (ultimos 10 mensajes)
   |  6d. Llama al LLM (Gemini 2.5 Flash, ~4-8s)
   |  6e. Guarda mensaje + respuesta en ai_conversations
   |  6f. Notifica via WebSocket al frontend (panel Prospectos)
   |  6g. Retorna { response, conversation_id, confianza, sub_agente_usado }
   |
7. api_execute: post-procesamiento
   |  7a. Extrae JSON de pedido confirmado (si existe)
   |  7b. Crea comanda automatica (si pedido_confirmado=true + lead_id)
   |  7c. Stripea bloque JSON del response (no se envia al cliente)
   |  7d. Retorna response limpio a canales-service
   |
8. canales-service: envia respuesta al cliente via Evolution API
```

---

## Donde vive cada pieza del prompt

### Layer 1: System Prompt Base
- **Tabla**: `agente_config` (columna `system_prompt`)
- **Configurable**: Si, desde el frontend en Configuracion > Agente IA
- **Fallback**: Si no hay config, se auto-genera: "Eres el asistente virtual de {nombre_tenant}..."
- **Archivo**: `api_execute/app/services/ai_orchestrator.py` → `_load_agent_config()`

### Layer 2: Knowledge Context
- **Tabla**: `tenant_knowledge` (columnas `type`, `title`, `content`, `priority`)
- **Tipos**: HORARIO, FAQ, DELIVERY, POLITICA, GENERAL, etc
- **Formato en prompt**: `[TIPO] Titulo:\nContenido`
- **Archivo**: `api_execute/app/services/ai_orchestrator.py` → `_load_knowledge_context()`

### Layer 3: Catalogo de Productos + Reglas Cotizador
- **Tabla**: `productos` + `modifier_groups` + `modifiers` + `producto_modifier_groups`
- **Solo se incluye si hay productos activos** para el tenant
- **Formato en prompt**:
  ```
  Catalogo de productos:
  - Pizza Margarita: $8500 — Tomate, mozzarella, albahaca (ID: uuid)
    * Tamano (elegir 1) [OBLIGATORIO]:
      - Individual: $0 (ID: uuid)
      - Familiar: +$4000 (ID: uuid)
    * Extras (elegir varios):
      - Extra queso: +$1500 (ID: uuid)
  - [NO DISPONIBLE] Pasta Carbonara: $7200 (ID: uuid)
  ```
- **Reglas**: `COTIZADOR_RULES` en `ai_orchestrator.py` — instrucciones para actuar como mozo virtual
- **Archivo**: `api_execute/app/services/ai_orchestrator.py` → `_load_product_catalog()`

### Layer 4: Behavioral Rules (ai_dialer)
- **Constante**: `BEHAVIORAL_RULES` en `AI_dialer/app/services/chat_service.py`
- **No configurable por tenant** — son reglas genericas que aplican siempre
- **Contenido**:
  - No re-saludar si hay historial
  - No repetir frases en respuestas consecutivas
  - No inventar informacion que no este en el contexto
  - Ser conciso, no repetir el catalogo completo en cada respuesta
  - Si no sabe, decir que no sabe

### Layer 5: Historial de Conversacion
- **Tabla**: `ai_conversations` (columna `messages` JSONB)
- **Cantidad**: Ultimos 10 mensajes
- **Archivo**: `AI_dialer/app/services/chat_service.py` → `_get_conversation_history()`

### Prompt final que recibe el LLM

```
[System Message]
{system_prompt del tenant}                    ← Layer 1
{knowledge context}                           ← Layer 2
{COTIZADOR_RULES}                             ← Layer 3 (si hay productos)
{instrucciones_disponibilidad}                ← Layer 3 (opcional)
{catalogo de productos formateado}            ← Layer 3
{BEHAVIORAL_RULES}                            ← Layer 4

[Mensajes]
user: mensaje anterior del cliente            ← Layer 5
assistant: respuesta anterior de la IA        ← Layer 5
...
user: "Quiero una pizza margarita"            ← Mensaje actual
```

---

## Modos de operacion de ai_dialer

### Modo Orchestrated (system_prompt_override presente)
- **Quien lo usa**: api_execute (via canal WhatsApp)
- **Que hace**: Usa el prompt recibido tal cual + agrega BEHAVIORAL_RULES
- **NO hace**: Clasificacion de intent, ruteo a sub-agentes, carga de config/knowledge
- **Sub-agente reportado**: `"ORCHESTRATED"`
- **Confianza reportada**: `0.95` (fija)

### Modo Legacy (sin system_prompt_override)
- **Quien lo usa**: Frontend web chat (llamadas directas a ai-dialer)
- **Que hace**: Todo el pipeline completo:
  1. Carga agente_config
  2. Carga knowledge via `build_knowledge_context()`
  3. Clasifica intent (PEDIDO, MENU, RESERVA, etc)
  4. Rutea a sub-agente (Cotizador, Seguimiento, RAG, FAQ)
  5. Genera respuesta
- **Sub-agentes**: RAG, COTIZADOR, SEGUIMIENTO, FAQ

> **Nota**: El modo legacy se mantiene por backward compatibility. A futuro, el frontend
> tambien deberia pasar por api_execute para unificar el flujo.

---

## Configuracion del LLM

### Parametros por defecto
| Parametro | Valor | Configurable |
|-----------|-------|-------------|
| Provider | `gemini` | Si, env var `LLM_PROVIDER` |
| Modelo | `gemini-2.5-flash` | Si, `agente_config.modelo` |
| Temperatura | `0.7` | Si, `agente_config.temperatura` |
| Max tokens | `1024` | Si, `agente_config.max_tokens` |
| Umbral confianza | `0.85` | Si, `agente_config.umbral_confianza` |
| Embeddings | OpenAI `text-embedding-3-small` | No (siempre OpenAI) |

### API Keys
| Key | Uso | Donde esta |
|-----|-----|-----------|
| `OPENAI_API_KEY` | Embeddings (text-embedding-3-small) | ai-dialer, callback-manual |
| `GEMINI_API_KEY` | LLM (gemini-2.5-flash) | ai-dialer |
| Per-tenant keys | Override via `llm_provider_keys` tabla | DB (encrypted) |

### Endpoints LLM
| Provider | Base URL | Modelo |
|----------|----------|--------|
| `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |

---

## Post-procesamiento de pedidos

Cuando el LLM genera una respuesta que contiene un pedido confirmado:

1. **Deteccion**: `extract_order_json()` busca bloques ` ```json ... ``` ` en la respuesta
2. **Validacion**: Verifica que `pedido_confirmado: true` este presente
3. **Creacion de comanda**: `_create_comanda_from_order()` crea un registro en la tabla `comandas` con los items del pedido
4. **Limpieza**: `_strip_json_block()` remueve el JSON de la respuesta antes de enviar al cliente
5. **Resultado**: El cliente recibe solo el texto del resumen, nunca el JSON

### Formato JSON que el LLM genera (instrucciones en COTIZADOR_RULES)
```json
{
  "pedido_confirmado": true,
  "tipo_entrega": "MESA|DELIVERY|RETIRO",
  "numero_mesa": null,
  "items": [
    {
      "producto_id": "uuid-del-producto",
      "cantidad": 1,
      "modifiers_json": [{"modifier_id": "uuid-del-modifier"}],
      "notas": "nota especial o null"
    }
  ]
}
```

---

## Archivos clave

| Archivo | Lineas | Responsabilidad |
|---------|--------|-----------------|
| `api_execute/app/services/ai_orchestrator.py` | ~360 | Orquestador: prompt builder, forward, post-process |
| `api_execute/app/routes/ai_orchestrator.py` | ~65 | Endpoint POST /process-message |
| `api_execute/app/schemas/ai_orchestrator.py` | ~25 | Request/Response Pydantic models |
| `AI_dialer/app/services/chat_service.py` | ~750 | Motor IA: classify, sub-agents, LLM call, history |
| `AI_dialer/app/services/classify_service.py` | ~120 | Clasificacion de intents |
| `AI_dialer/app/services/rag_agent.py` | ~80 | Sub-agente RAG (embeddings + search) |
| `AI_dialer/app/services/cotizador_agent.py` | ~100 | Sub-agente Cotizador (fetch productos) |
| `AI_dialer/app/services/llm_service.py` | ~80 | Wrapper de llamadas al LLM |
| `AI_dialer/app/services/embedding_service.py` | ~60 | Generacion de embeddings |
| `canales_service/app/services/whatsapp_service.py` | ~900 | Gateway WhatsApp (webhook → orquestador) |

---

## Tabla de intents y sub-agentes

| Intent | Sub-agente | Que hace |
|--------|-----------|---------|
| PEDIDO | COTIZADOR | Muestra menu, toma pedido, calcula total, genera JSON comanda |
| MENU | COTIZADOR | Muestra menu y precios |
| COTIZACION | COTIZADOR | Cotiza combos o eventos |
| SEGUIMIENTO | SEGUIMIENTO | Historial del cliente, pedidos anteriores, fidelizacion |
| CONSULTA | RAG | Busca en knowledge base del tenant |
| RESERVA | RAG | Informacion sobre reservas |
| DELIVERY | RAG | Informacion sobre delivery/zonas |
| SOPORTE | RAG | Soporte general |
| QUEJA | RAG | Manejo de quejas (low confidence → human review) |
| FAQ | FAQ | Preguntas frecuentes |
| OTRO | RAG | Fallback |

> **Nota**: En modo orchestrated (WhatsApp), la clasificacion NO se ejecuta.
> El catalogo y reglas de cotizador van directo en el system prompt, y el LLM
> decide por si solo si el cliente quiere pedir, consultar, etc.

---

## Confianza y revision humana

| Confianza | Accion |
|-----------|--------|
| >= 0.85 | Respuesta se envia automaticamente al cliente |
| < 0.85 | Se crea entrada en `revision_humana`, notifica a callback-manual, un humano aprueba/edita/rechaza |

En modo orchestrated, la confianza es fija en `0.95` (siempre auto-send).

---

## Incidentes y fixes aplicados

| Fecha | Problema | Causa | Fix |
|-------|----------|-------|-----|
| 2026-03-13 | IA saludaba en cada mensaje | No se pasaba historial al LLM | `_get_conversation_history()` + BEHAVIORAL_RULES |
| 2026-03-13 | Precios incorrectos | ai_dialer cargaba config sin catalogo real | Refactor: api_execute carga catalogo real de DB |
| 2026-03-14 | 403 canales→api_execute | `ai_orchestrator.py` usaba `get_current_user` | Cambiado a `require_user_or_service(service_callers=("canales_service",))` |
| 2026-03-14 | 403 api_execute→ai_dialer | chat.py no incluia `api_execute` en callers | Agregado `"api_execute"` a `service_callers` tuple |
| 2026-03-14 | JSON de pedido enviado al cliente | No se stripeaba el bloque JSON | `_strip_json_block()` en ai_orchestrator |
| 2026-03-14 | 502 en /process-message | Columna `modifier_group_id` no existe | Corregido a `grupo_id` + try/except resiliente |

---

## Proximos pasos

1. **Unificar frontend web chat**: Que el chat del panel tambien pase por api_execute en vez de ir directo a ai_dialer (eliminar modo legacy)
2. **Imagenes de productos en prompt**: Evaluar si enviar URLs de imagenes al LLM mejora las recomendaciones
3. **Streaming de respuestas**: SSE/WebSocket para mostrar respuesta caracter a caracter en el panel
4. **Fine-tuning de COTIZADOR_RULES**: Ajustar basado en feedback real de restaurantes
5. **Cache de system_message**: El prompt se reconstruye en cada mensaje — cachear por tenant_id con TTL de 5min
6. **Metricas de IA**: Latencia promedio, tokens usados, ratio de human review, pedidos auto-confirmados
