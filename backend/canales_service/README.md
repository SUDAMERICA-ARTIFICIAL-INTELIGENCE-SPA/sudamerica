# sudamerica-canales-service

Servicio dedicado a la conexion y operacion de canales de usuario.

## Responsabilidades

- Crear y reconectar instancias de WhatsApp en Evolution API.
- Exponer QR para onboarding de WhatsApp por tenant.
- Aplicar configuracion defensiva de instancias.
- Recibir webhooks de Evolution y reenviar mensajes a `api_execute` (POST `/ai/process-message`).
- Enviar respuestas de WhatsApp usando la instancia registrada del tenant.

## Endpoints

```text
POST /api/v1/canales/qr/{tenant_id}
GET  /api/v1/canales/qr/{tenant_id}/status
POST /api/v1/canales/whatsapp/send
POST /api/v1/canales/whatsapp/instance/{tenant_id}/settings
POST /api/v1/canales/webhook/whatsapp
GET  /health
GET  /health/ready
```

## Setup local

```bash
cp .env.example .env
pip install -r requirements.txt
pip install -e ../shared
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

## Variables de entorno

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Clave JWT para tokens de usuario |
| `JWT_ALGORITHM` | Algoritmo JWT |
| `CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY` | Clave HMAC propia del emisor `canales_service` para JWT internos |
| `API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY`, `CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY`, `TASKS_INTERNAL_SERVICE_SECRET_KEY` | Claves confiadas por issuer para verificar JWT internos |
| `EVOLUTION_API_URL` | Base URL de Evolution API |
| `EVOLUTION_API_KEY` | API key de Evolution |
| `EVOLUTION_WEBHOOK_URL` | Webhook publico que Evolution debe invocar |
| `WEBHOOK_TOKEN` | Token obligatorio para registrar y aceptar webhooks de Evolution |
| `SERVICE_API_EXECUTE_URL` | URL interna de `api_execute` |
| `FRONTEND_URL` | URL del frontend |

## Tests

```bash
pytest canales_service/tests -q
```
