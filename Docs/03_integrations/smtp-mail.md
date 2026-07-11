# SMTP / Email Transaccional — Sudamérica AI

## Proveedor: Resend
- **Cuenta**: benjamin@sudamerica.ai (login con Google)
- **Plan**: Free (100 emails/dia)
- **Region**: us-east-1
- **Domain ID**: `b29c8119-092c-4503-8a02-50c269337da2`
- **From**: `noreply@sudamerica.ai`

## API Keys

| Key | Permisos | Uso |
|---|---|---|
| `re_fpFpwftp_MiZsgb3fzESk3U7VVW8hLnXh` | Sending only | SMTP password en tasks service |
| `re_AH9gVjgH_CGZ6uEhnqiW9yWQNnM7ZQzX3` | Full access | Administracion (dominios, verificacion) |

## SMTP Config (ya configurado en Cloud Run - tasks service)

```
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=re_fpFpwftp_MiZsgb3fzESk3U7VVW8hLnXh
SMTP_FROM_EMAIL=noreply@sudamerica.ai
SMTP_FROM_NAME=Sudamérica AI
```

## Registros DNS — PENDIENTE (Cloudflare, dominio sudamerica.ai)

El socio que administra el dominio en Cloudflare debe agregar estos 3 registros:

### Registro 1 — DKIM
- **Tipo**: TXT
- **Nombre**: `resend._domainkey`
- **Valor**: `p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC8w+HSZJ8enpSaQwnCChNrcv2ynngeqE3UT1yFBpCVmrCd5IKUxYXrlib7Xdjpq/5WXvAmEEydRBei+ucx3grBmyI89I5lp6zkw3XHiFngrH0ztcWsNka0uT8wk/W9ykXQ/4PLRh3s2+8W+UPVQNpezQj49f9XjhUEHKv2sgxgSQIDAQAB`
- **TTL**: Auto

### Registro 2 — MX (SPF bounce handling)
- **Tipo**: MX
- **Nombre**: `send`
- **Valor**: `feedback-smtp.us-east-1.amazonses.com`
- **Prioridad**: 10
- **TTL**: Auto

### Registro 3 — SPF
- **Tipo**: TXT
- **Nombre**: `send`
- **Valor**: `v=spf1 include:amazonses.com ~all`
- **TTL**: Auto

## Verificar estado del dominio

Despues de que se agreguen los registros DNS, verificar con:

```bash
curl -s https://api.resend.com/domains/b29c8119-092c-4503-8a02-50c269337da2 \
  -H "Authorization: Bearer re_AH9gVjgH_CGZ6uEhnqiW9yWQNnM7ZQzX3"
```

El `status` debe cambiar de `not_started` a `verified`.

Tambien se puede forzar la verificacion:

```bash
curl -s -X POST https://api.resend.com/domains/b29c8119-092c-4503-8a02-50c269337da2/verify \
  -H "Authorization: Bearer re_AH9gVjgH_CGZ6uEhnqiW9yWQNnM7ZQzX3"
```

## Emails que envia el sistema

| Trigger | Subject | Template |
|---|---|---|
| POST /auth/forgot-password | Restablecer contraseña — Sudamérica AI | `shared/utils/email_templates.py::password_reset_email` |
| POST /auth/resend-verification | Verifica tu email — Sudamérica AI | `shared/utils/email_templates.py::email_verification_email` |
| Verificacion exitosa | (futuro) Bienvenido — Sudamérica AI | `shared/utils/email_templates.py::welcome_email` |

## Flujo tecnico

```
api_execute (genera token)
  → POST tasks/api/v1/tasks/email/send (inter-service auth)
    → tasks/email_service.py (aiosmtplib + STARTTLS)
      → smtp.resend.com:587
        → noreply@sudamerica.ai → usuario
```

## Troubleshooting

- **Emails no llegan**: Verificar que los 3 registros DNS esten propagados (`dig TXT resend._domainkey.sudamerica.ai`)
- **401 en Resend**: La API key de sending (`re_fpF...`) solo puede enviar, no administrar
- **Timeout SMTP**: Verificar que tasks service tenga acceso de red a smtp.resend.com:587
- **Emails en spam**: Los registros DKIM/SPF deben estar verificados. Considerar agregar DMARC:
  - Tipo: TXT, Nombre: `_dmarc`, Valor: `v=DMARC1; p=none; rua=mailto:benjamin@sudamerica.ai`
