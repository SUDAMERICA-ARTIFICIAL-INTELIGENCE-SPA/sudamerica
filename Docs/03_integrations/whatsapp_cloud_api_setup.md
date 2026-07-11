# WhatsApp Business Cloud API — Guía de Setup

## ¿Por qué migrar de Baileys a Cloud API?

| | Baileys (anterior) | Cloud API (nuevo) |
|---|---|---|
| IP bloqueada | Sí, Meta bloquea IPs de datacenter | No, es la API oficial |
| Multi-tenant | Frágil, sesiones se caen | Diseñado para multi-tenant |
| QR scan | Requerido cada vez que se desconecta | No necesario, es por token |
| Uptime | Depende de WebSocket persistente | 99.9% SLA de Meta |

## Paso 1: Crear cuenta Meta Business (5 min)

1. Ve a https://business.facebook.com
2. Crea una cuenta de negocios (o usa una existente)
3. Anota tu **Business ID** (en Configuración > Info del negocio)

## Paso 2: Crear app en Facebook Developers (5 min)

1. Ve a https://developers.facebook.com
2. Click "Crear app" → Tipo: **Negocio**
3. Agrega el producto **WhatsApp** a la app
4. En WhatsApp > Configuración de API:
   - Verás tu **Phone Number ID** (número de prueba gratuito)
   - Verás tu **WhatsApp Business Account ID**

## Paso 3: Generar Token Permanente (3 min)

1. En la app de Facebook Developers, ve a **Configuración > Básica**
2. Ve a https://developers.facebook.com/tools/explorer
3. Selecciona tu app
4. Genera un **System User Token** con permisos:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`
5. Crea un System User en Business Manager:
   - Business Settings > Users > System Users > Add
   - Asigna la app con permisos completos
   - Genera token permanente

## Paso 4: Configurar Webhook de Meta (3 min)

En Facebook Developers > WhatsApp > Configuración:

1. **Webhook URL**: `https://evolution-api-456595931835.us-central1.run.app/webhook/meta`
2. **Verify Token**: El valor de `WA_BUSINESS_TOKEN_WEBHOOK` (configurado en Evolution API)
3. **Suscribirse a**: `messages`

## Paso 5: Registrar instancia en Sudamérica AI (1 min)

```bash
# Via API (reemplaza los valores):
curl -X POST "https://canales-service-456595931835.us-central1.run.app/api/v1/canales/cloud-api/{TENANT_ID}" \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "meta_token": "TU_TOKEN_PERMANENTE_DE_META",
    "meta_number_id": "TU_PHONE_NUMBER_ID",
    "meta_business_id": "TU_WHATSAPP_BUSINESS_ACCOUNT_ID",
    "phone_number": "+56912345678"
  }'
```

O desde el frontend (cuando se agregue el UI): Canales > WhatsApp > "Conectar con Cloud API"

## Paso 6: Verificar conexión

```bash
# Verificar estado de la instancia:
curl "https://canales-service-456595931835.us-central1.run.app/api/v1/canales/qr/{TENANT_ID}/status" \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

Debería retornar `status: "open"` y `integration: "WHATSAPP-BUSINESS"`.

## Variables de entorno necesarias

### En Evolution API (Cloud Run):
```
WA_BUSINESS_TOKEN_WEBHOOK=<token-para-verificar-webhooks-de-meta>
```

### En canales-service (Cloud Run):
```
WA_BUSINESS_TOKEN_WEBHOOK=<mismo-token-que-evolution-api>
```

## Número de prueba gratuito

Meta proporciona un número de prueba gratuito al crear la app. Puedes:
- Enviar mensajes a hasta 5 números verificados (gratis)
- Después de verificar tu negocio: enviar a cualquier número

## Costos

- **Conversaciones iniciadas por el usuario** (24h window): GRATIS
- **Conversaciones iniciadas por el negocio** (templates): ~$0.01-0.05 USD por mensaje
- **1,000 conversaciones de servicio al mes**: GRATIS (Meta incluye esto)

## Compatibilidad

El endpoint de envío de mensajes es el mismo — Evolution API abstrae la diferencia entre Baileys y Cloud API. Canales-service envía via `/message/sendText/{instance}` y Evolution se encarga del resto.

Los webhooks de recepción también llegan al mismo endpoint de canales-service (`/webhook/whatsapp`), ya que Evolution normaliza el formato.
