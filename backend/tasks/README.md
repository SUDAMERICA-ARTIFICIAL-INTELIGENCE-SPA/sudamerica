# sudamerica-tasks

Servicio de tareas asincronas del backend de Sudamérica AI.

## Responsabilidad actual

- Envio de emails via SMTP.
- Punto natural para futuras ejecuciones asincronas post-callback.
- No administra onboarding ni conexion de canales sociales.

## Endpoints

```text
POST /api/v1/tasks/email/send
GET  /health
GET  /health/ready
```

## Setup local

```bash
cp .env.example .env
pip install -r requirements.txt
pip install -e ../shared
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Variables de entorno

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Clave JWT para tokens de usuario |
| `JWT_ALGORITHM` | Algoritmo JWT |
| `TASKS_INTERNAL_SERVICE_SECRET_KEY` | Clave HMAC propia del emisor `tasks` para JWT internos |
| `API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY`, `CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY`, `CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY` | Claves confiadas por issuer para verificar JWT internos |
| `SMTP_HOST` | Servidor SMTP |
| `SMTP_PORT` | Puerto SMTP |
| `SMTP_USER` | Usuario SMTP |
| `SMTP_PASSWORD` | Password SMTP |
| `SMTP_FROM_EMAIL` | Remitente |
| `SMTP_FROM_NAME` | Nombre remitente |
| `FRONTEND_URL` | URL del frontend |

## Tests

```bash
pytest tasks/tests -q
```
