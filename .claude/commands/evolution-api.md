# Skill: Evolution API — Sudamérica AI

## Identidad
- **Rol**: Evolution API WhatsApp Integration Specialist
- **Nivel**: Infraestructura + Integracion
- **Especialidad**: Evolution API v2 (Baileys), WhatsApp Business, webhooks, mensajes interactivos

## Infraestructura

### VM en Compute Engine (NO Cloud Run)
- **VM**: `evolution-api-vm` en `us-central1-f`
- **IP fija**: `34.61.234.182:8080`
- **API Key**: `08d58d981ede7e23032bb060d30999c0e1b061da126f16dcbc3d14a6fa704e43`
- **Razon**: Meta bloquea rangos de IPs compartidas de Cloud Run. IP dedicada obligatoria.

### Gestion de la VM
```bash
# SSH
gcloud compute ssh evolution-api-vm --zone us-central1-f --project sudamerica-prod

# Logs
docker logs evolution-api --tail 100

# Restart
docker restart evolution-api
```

## Endpoints Evolution API v2

### Envio de mensajes
```
POST /message/sendText/{instance_name}      → Texto simple
POST /message/sendMedia/{instance_name}     → Imagen, PDF, video, audio
POST /message/sendPoll/{instance_name}      → Encuesta interactiva (FUNCIONA)
POST /message/sendList/{instance_name}      → Lista interactiva (ROTO en Baileys v2 — error isZero)
POST /message/sendButtons/{instance_name}   → Botones (parcialmente funcional)
POST /chat/sendPresence/{instance_name}     → Indicador "escribiendo..."
```

### Instancias
```
GET  /instance/fetchInstances               → Listar instancias
POST /instance/create                       → Crear instancia
GET  /instance/connectionState/{instance}   → Estado de conexion
POST /instance/connect/{instance}           → Generar QR
DELETE /instance/delete/{instance}          → Eliminar instancia
```

### Webhook
```
GET  /webhook/find/{instance}               → Ver config actual
POST /webhook/set/{instance}                → Configurar webhook
```

## Payloads de mensajes

### sendText
```json
{"number": "56912345678", "text": "Hola!"}
```

### sendPoll (RECOMENDADO para opciones)
```json
{
  "number": "56912345678",
  "name": "¿En que te puedo ayudar?",
  "selectableCount": 1,
  "values": ["Hacer un pedido", "Ver el menu", "Reservar mesa"]
}
```

### sendMedia (imagen, PDF, documento)
```json
{
  "number": "56912345678",
  "mediatype": "document",
  "media": "https://url-del-archivo.pdf",
  "fileName": "Menu.pdf",
  "caption": "Aqui esta nuestro menu",
  "mimetype": "application/pdf"
}
```

### sendList (ROTO — no usar)
```json
{
  "number": "56912345678",
  "title": "Opciones",
  "description": "Elige",
  "buttonText": "Ver",
  "sections": [{"title": "Sec", "rows": [{"title": "Op1", "rowId": "op1"}]}]
}
```
**NOTA**: `sendList` falla con `TypeError: this.isZero is not a function` en Baileys. Usar `sendPoll` como alternativa.

## Webhook — Eventos y Payloads

### Eventos obligatorios
```json
{
  "webhook": {
    "url": "https://canales-service-456595931835.us-central1.run.app/api/v1/canales/webhook/whatsapp",
    "headers": {"apikey": "<WEBHOOK_TOKEN>"},
    "enabled": true,
    "events": ["QRCODE_UPDATED", "MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
  }
}
```

**CRITICO**: `MESSAGES_UPDATE` es OBLIGATORIO para recibir votos de polls.

### Configurar webhook
```bash
curl -X POST "http://34.61.234.182:8080/webhook/set/{instance_name}" \
  -H "apikey: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"webhook": {"url": "...", "headers": {"apikey": "..."}, "enabled": true, "events": ["QRCODE_UPDATED", "MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]}}'
```

### Payload: Mensaje de texto entrante (MESSAGES_UPSERT)
```json
{
  "event": "messages.upsert",
  "instance": "tenant-{uuid}",
  "data": {
    "key": {"remoteJid": "56912345678@s.whatsapp.net", "fromMe": false, "id": "MSG_ID"},
    "pushName": "Juan",
    "message": {"conversation": "Hola quiero pedir"},
    "messageType": "conversation",
    "messageTimestamp": 1775952113
  }
}
```

### Payload: Voto de poll (MESSAGES_UPSERT con pollUpdates)

**IMPORTANTE**: Los votos llegan como `messages.upsert`, NO como `messages.update`.

```json
{
  "event": "messages.upsert",
  "data": {
    "key": {
      "remoteJid": "56923812710@s.whatsapp.net",
      "fromMe": false,
      "id": "A5D041BEF2BA17D8846DBBB5145F4C8C"
    },
    "message": {
      "pollUpdateMessage": {
        "pollCreationMessageKey": {"remoteJid": "...@lid", "fromMe": true, "id": "POLL_CREATION_ID"},
        "vote": {
          "selectedOptions": ["Hacer un pedido"],
          "encPayload": {"0": 89, "1": 212, ...}
        }
      }
    },
    "messageType": "pollUpdateMessage",
    "pollUpdates": [
      {"name": "Hacer un pedido", "voters": ["81459071209727@lid"]},
      {"name": "Ver el menu", "voters": []},
      {"name": "Reservar mesa", "voters": []},
      {"name": "Delivery", "voters": []},
      {"name": "Consultar estado", "voters": []}
    ]
  }
}
```

**Como extraer la opcion seleccionada**:
- `data.pollUpdates` es un array con TODAS las opciones del poll
- La opcion seleccionada es la que tiene `voters` NO vacio
- `data.message.pollUpdateMessage.vote.selectedOptions[0]` tambien tiene el texto (redundante)
- El votante real: `data.key.remoteJid` (JID del que voto)
- Los voters en pollUpdates usan `@lid` (LinkedIn ID interno de WhatsApp), no `@s.whatsapp.net`

### Payload: Respuesta a lista interactiva (MESSAGES_UPSERT)
```json
{
  "event": "messages.upsert",
  "data": {
    "key": {"remoteJid": "56912345678@s.whatsapp.net", "fromMe": false},
    "message": {
      "listResponseMessage": {
        "title": "Hacer un pedido",
        "listType": 1,
        "singleSelectReply": {"selectedRowId": "hacer_un_pedido"}
      }
    }
  }
}
```

### Payload: Status update (MESSAGES_UPDATE — no es voto)
```json
{
  "event": "messages.update",
  "data": {
    "keyId": "MSG_ID",
    "remoteJid": "56912345678@s.whatsapp.net",
    "fromMe": true,
    "status": "DELIVERY_ACK",
    "instanceId": "...",
    "messageId": "..."
  }
}
```
**NOTA**: Los `messages.update` con status (DELIVERY_ACK, READ, etc.) NO son votos. Solo contienen `status` sin `pollUpdates`.

## Parsing en canales_service

### Cadena de extraccion de texto (`_extract_text`)
```python
_conversation_text(msg)     # msg.conversation
_extended_text(msg)         # msg.extendedTextMessage.text
_list_response_text(msg)    # msg.listResponseMessage.title
_button_response_text(msg)  # msg.buttonsResponseMessage.selectedDisplayText
_caption_text(msg)          # msg.imageMessage.caption, etc.
```

### Extraccion de votos de poll
Los polls se manejan ANTES de `_extract_text` porque el payload es distinto:
1. `_find_poll_updates(payload)`: Busca `pollUpdates` en `data.pollUpdates`, `data.update.pollUpdates`, o `data[i].update.pollUpdates`
2. `_extract_poll_vote_text(poll_updates)`: Formato A (aggregated): busca `name` con `voters` no vacio. Formato B (individual): lee `vote[]`
3. `_find_poll_voter(payload, poll_updates)`: Extrae voter JID de `pollUpdateMessageKey.participant`, `data.key.remoteJid`, etc.
4. Se construye mensaje sintetico `{"sender": voter_jid, "message": vote_text, "from_me": false}` y se procesa como mensaje normal

## Marcadores interactivos (AI → WhatsApp)

El orquestador (`ai_orchestrator.py`) genera marcadores que `canales_service` resuelve:

| Marcador | Resolucion |
|----------|-----------|
| `[ENVIAR_POLL:pregunta\|op1\|op2\|op3]` | `send_poll()` via Evolution API |
| `[ENVIAR_LISTA:titulo\|boton\|sec:op1,op2]` | `send_list()` → fallback a `send_poll()` si falla |
| `[ENVIAR_MENU]` o `[ENVIAR_MENU_PDF]` | `send_media()` con PDF + opcional cabecera imagen |
| `[ENVIAR_IMAGEN:nombre_producto]` | `send_media()` con imagen del producto |
| `[ALERTA_MESERO]` | Notificacion interna (mesa action) |
| `[PEDIR_CUENTA]` | Notificacion interna (mesa action) |

**Fallback programatico**: Si la IA no incluye marcadores, el orquestador inyecta un poll de bienvenida/sucursal automaticamente.

## Settings de instancia (anti-ban)

```json
{
  "rejectCall": true,
  "msgCall": "Llamada no disponible",
  "groupsIgnore": true,
  "alwaysOnline": true,
  "readMessages": true,
  "readStatus": false
}
```

## Troubleshooting

### Poll votes no llegan
1. Verificar que `MESSAGES_UPDATE` esta en los eventos del webhook: `GET /webhook/find/{instance}`
2. Si falta, agregar: `POST /webhook/set/{instance}` con `events` completo
3. Los votos llegan como `messages.upsert` con `messageType: "pollUpdateMessage"` y `data.pollUpdates`

### sendList error "isZero"
- Bug de Baileys. No hay fix. Usar `sendPoll` como alternativa
- El fallback en canales_service convierte listas a polls automaticamente

### Mensajes duplicados
- Verificar dedup cache en canales_service (60s TTL, clave: `message_id`)
- Los poll votes generan un `message_id` unico — el dedup los maneja

### Instancia desconectada
```bash
# Verificar estado
curl "http://34.61.234.182:8080/instance/connectionState/{instance}" -H "apikey: <KEY>"

# Si state != "open": regenerar QR desde frontend o via API
curl -X POST "http://34.61.234.182:8080/instance/connect/{instance}" -H "apikey: <KEY>"
```

### Meta bloquea la IP
- La VM tiene IP `34.61.234.182`. Si Meta la bloquea:
  1. Reservar nueva IP estatica: `gcloud compute addresses create evo-ip-v2 --region us-central1`
  2. Asignar a la VM
  3. Actualizar `SERVER_URL` en el container Evolution API
  4. Actualizar `EVOLUTION_API_URL` en canales-service
