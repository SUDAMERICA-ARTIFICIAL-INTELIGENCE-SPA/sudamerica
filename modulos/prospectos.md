# Modulo: Prospectos — Integración WhatsApp + Seguimiento Conversaciones IA

## Objetivo
Permitir al usuario del sistema conectar su WhatsApp escaneando un QR, y hacer seguimiento en tiempo real de las conversaciones que la IA tiene con sus clientes (prospectos) a través de WhatsApp.

## Stack
- **Backend:** FastAPI (tasks :8003 + AI_dialer :8001)
- **Frontend:** Next.js 15 + Mantine 7 + TanStack Query v5
- **WhatsApp:** Evolution API (self-hosted, Baileys lib)
- **LLM:** OpenRouter (multi-provider)

## Arquitectura

```
[Cliente WhatsApp]
        ↕ WebSocket/Proto
[Evolution API] (VPS/Docker)
        ↕ HTTP REST
[tasks :8003]
  ├─ POST /webhook/whatsapp     ← recibe mensajes entrantes (sin auth)
  ├─ POST /whatsapp/send        ← envía respuesta IA (con auth)
  ├─ POST /qr/{tenant_id}      ← genera instancia + QR
  └─ GET  /qr/{tenant_id}/status ← estado conexión
        ↓ forward
[AI_dialer :8001]
  ├─ POST /chat                 ← procesa mensaje → classify → sub-agent → LLM
  ├─ GET  /conversations        ← lista hilos de conversación por tenant (NUEVO)
  └─ GET  /conversations/{lead_id}/messages ← mensajes de un hilo (NUEVO)
        ↓ persiste
[PostgreSQL] ai_conversations (tenant_id, lead_id, role, content, canal, created_at)
```

## Flujo Completo

### 1. Conexión WhatsApp (QR)
1. Admin va a `/prospectos` → click "Conectar WhatsApp"
2. Frontend: `POST /api/v1/canales/qr/{tenant_id}` → crea instancia Evolution API
3. Backend retorna QR en base64 → frontend lo renderiza
4. Usuario escanea QR con WhatsApp físico
5. Frontend polling: `GET /api/v1/canales/qr/{tenant_id}/status` cada 3s
6. Cuando `status === "open"` → WhatsApp conectado → auto-configura webhook

### 2. Recepción de Mensajes (Prospecto → IA)
1. Evolution API recibe mensaje → webhook → `POST /webhook/whatsapp`
2. tasks parsea payload: `sender` (remoteJid), `message` (text), `instance_name`
3. tasks extrae `tenant_id` del `instance_name` (pattern: `tenant-{uuid}`)
4. tasks busca/crea lead en api_execute por `telefono=sender`
5. tasks forward a AI_dialer: `POST /chat` con `{message, lead_id, canal: "WHATSAPP"}`
6. AI_dialer: classify → sub-agent → LLM → guarda en ai_conversations
7. Si confianza >= 0.85: tasks envía respuesta vía Evolution API `sendText`
8. Si confianza < 0.85: callback_manual recibe para revisión humana

### 3. Seguimiento de Conversaciones (Frontend)
1. Vista `/prospectos` muestra lista de threads (agrupados por lead_id)
2. Click en thread → abre panel de chat con historial completo
3. Cada mensaje muestra: role (user/assistant), timestamp, canal, confianza
4. Badge: "Auto" (verde) si resuelto sin humano, "Revisado" (amarillo) si requirió revisión

## Endpoints Backend (Nuevos)

### AI_dialer — Conversaciones
```
GET /api/v1/ai/conversations
  Query: ?page=1&page_size=20&canal=WHATSAPP
  Response: PaginatedResponse<ConversationThread>

GET /api/v1/ai/conversations/{lead_id}/messages
  Query: ?page=1&page_size=50
  Response: PaginatedResponse<ConversationMessage>
```

### Tasks — Mejoras al webhook
```
POST /api/v1/canales/webhook/whatsapp
  Mejora: auto-crear lead en api_execute si no existe
  Mejora: enviar respuesta IA de vuelta vía Evolution API
  Mejora: latencia variable anti-ban (2-5s delay)

POST /api/v1/canales/whatsapp/instance/settings
  Body: {reject_call: true, always_online: true, read_messages: true}
  Configura instancia Evolution API con settings defensivos
```

## Frontend — Componentes

### Página: `/prospectos`
- **WhatsAppStatus**: Badge conexión (conectado/desconectado) + botón reconectar
- **QRModal**: Modal con QR code + polling de status + instrucciones
- **ConversationList**: Lista de threads por lead, último mensaje, timestamp, badge canal
- **ConversationChat**: Vista tipo chat con mensajes user/assistant, confidence badge
- **ProspectosFilters**: Filtros por canal, estado lead, fecha, búsqueda

### Hooks
- `useWhatsAppStatus()` — polling status conexión
- `useConversationThreads()` — lista de hilos
- `useConversationMessages(leadId)` — mensajes de un hilo

## Anti-Ban (Evolution API)
- Delay variable: `random.uniform(2, 5)` segundos antes de responder
- Config defensiva: `reject_call=true`, `always_online=true`, `read_messages=true`
- Volumen progresivo: <100 msgs/día primera semana
- No re-escanear QR múltiples veces en mismo dispositivo

## Quality Gates
- Tests unitarios para cada endpoint nuevo
- CC <= 12 por función
- Zero SAST findings (bandit)
- Todos los queries scoped por tenant_id
