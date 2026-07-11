# Plan de Lanzamiento y Facturación — Sudamérica AI / Sudamérica AI

> **Fecha**: 2026-06-11
> **Objetivo**: cerrar el MVP y empezar a facturar clientes reales.
> **Estado base**: registro + onboarding DEPLOYED y verificado E2E. Stripe SaaS completo a nivel código (falta solo configuración). P0 de producto pendientes según `funcionalidades_faltantes.md`.

---

## 1. Precios oficiales (fuente: https://www.sudamerica.ai/)

| Plan web | Precio | Incluye (web) | Plan app actual |
|---|---|---|---|
| **Emprendedor** | $0 /mes | 1 agente IA, 500 mensajes/mes, CRM básico | `ESTANDAR` (3 users, 100 leads/mes) |
| **Crecimiento** ★ | $29.990 CLP/mes +IVA | 3 agentes, mensajes ilimitados, omnicanal | `PLUS` (8 users, 500 leads/mes) |
| **Corporativo** | $74.990 CLP/mes +IVA | Agentes ilimitados, IA custom, SLA | `PRO` (20 users, ilimitado) |

**⚠️ Desalineamiento a resolver (decisión de producto):**
- Nombres: web dice Emprendedor/Crecimiento/Corporativo; la app dice Estandar/Plus/Pro.
- Límites: web habla de *agentes y mensajes*; la app limita *usuarios y leads/mes*.
- Recomendación: adoptar los nombres del sitio web como **labels** en `/billing` (manteniendo los valores internos `ESTANDAR/PLUS/PRO` en DB para no migrar datos) y homologar la tabla de límites.

## 2. Pasarela elegida: Mercado Pago (decidido 2026-06-11)

**IMPLEMENTADO 2026-06-11** — suscripciones mensuales vía `/preapproval` (la doc de MP confirma que Checkout Pro NO soporta pagos recurrentes; Checkout API/preapproval sí):

- `backend/api_execute/app/services/mercadopago_service.py` — crea la suscripción (init_point) y procesa webhooks con validación `x-signature` + idempotencia.
- `POST /api/v1/core/billing/create-checkout` — endpoint genérico, despacha por `PAYMENT_PROVIDER` (default `mercadopago`; `stripe` queda como vía internacional futura).
- `POST /api/v1/core/billing/webhook/mercadopago` — upgrade al plan al quedar `authorized`, downgrade a ESTANDAR en `cancelled`/`paused`.
- Frontend `/billing` con nombres y precios del sitio web.
- Cero migración de DB: idempotencia reutiliza `stripe_events` (prefijo `mp_`) y el preapproval_id se guarda en `tenants.stripe_subscription_id`.

**Env vars a configurar en api-execute cuando existan credenciales:**
```
MP_ACCESS_TOKEN=APP_USR-...        # producción (o TEST-... para sandbox)
MP_WEBHOOK_SECRET=...              # firma de webhooks (panel MP)
MP_PLAN_AMOUNT_PLUS=29990          # confirmar si debe incluir IVA (35688)
MP_PLAN_AMOUNT_PRO=74990           # confirmar si debe incluir IVA (89238)
```
**Webhook a registrar en el panel MP** (Tus integraciones → Webhooks):
`https://api-execute-456595931835.us-central1.run.app/api/v1/core/billing/webhook/mercadopago`
— evento: Planes y Suscripciones (`subscription_preapproval`).

⚠️ Pendiente de decisión: si el monto cobrado debe ser neto ($29.990) o con IVA incluido ($35.688). El sitio dice "+IVA", lo que sugiere cobrar 29.990 × 1,19.

## 3. Tabla de responsabilidades

### Lo hace Claude (desarrollo)

| # | Tarea | Depende de | Esfuerzo |
|---|---|---|---|
| C1 | ✅ HECHO (2026-06-11) — `/billing` con labels y precios del sitio web | — | — |
| C2 | ✅ HECHO (2026-06-11) — adapter Mercado Pago (preapproval + webhook idempotente) | — | — |
| C3 | Configurar env vars MP + registrar webhook en panel MP + prueba sandbox E2E (upgrade → PLUS; cancelación → downgrade) | B2 (cuenta + keys) | 0.5 día |
| C4 | Enforcement de límites de plan (verificar max_users/max_leads al hacer downgrade y bloqueos al exceder cuota) | — | 1 día |
| C5 | Email de confirmación de pago/bienvenida vía `tasks` | B4 (SMTP) | 0.5 día |
| C6 | P0-1: Notificaciones de estado de pedido al cliente (hook en `comanda_svc.transition_estado()` → WhatsApp) | — | 1-2 días |
| C7 | P0-2: Pago en conversación (link Mercado Pago Checkout Pro generado por la IA + webhook → comanda `EN_COCINA`) | B5 (modelo de cuentas MP por tenant) | 3-4 días |
| C8 | P0-3 + P0-4: encuestas post-servicio + "lo de siempre" | — | 1-2 días |
| C9 | Dominio custom: mapear `app.sudamerica.ai` → Cloud Run frontend + CORS/FRONTEND_URL | B6 (acceso DNS) | 0.5 día |
| C10 | Conectar CTA del sitio web ("Crear mi cuenta gratis") → `/register` de la app | B6 | trivial |

### Lo hace Benjamín (negocio / cuentas / legal)

| # | Tarea | Para qué | Urgencia |
|---|---|---|---|
| B1 | Confirmar: ¿el cobro mensual es $29.990 neto o $35.688 con IVA incluido? + ¿plan anual / trial? | montos en env | 🔴 Bloqueante |
| B2 | Crear cuenta Mercado Pago vendedor con datos de la SpA, verificación, cuenta bancaria para payouts; crear aplicación en [Tus integraciones](https://www.mercadopago.cl/developers/panel/app) y pasarme Access Token (TEST y PROD) + secret de webhook | C3 | 🔴 Bloqueante |
| B3 | Facturación electrónica SII: contratar emisor de boletas/facturas (OpenFactura/Haulmer, Bsale, o facturación manual al inicio) | legal para cobrar +IVA | 🔴 Antes del 1er cobro |
| B4 | Credenciales SMTP (Google Workspace u otro) para emails transaccionales | C5 | 🟡 |
| B5 | Decidir modelo de cobro de pedidos: ¿cada restaurante con su propia cuenta MP (marketplace/OAuth) o cuenta central de Sudamérica AI? | C7 | 🟡 |
| B6 | Acceso/delegación DNS de sudamerica.ai (o crear el registro CNAME que te indique) | C9, C10 | 🟡 |
| B7 | Términos y condiciones + política de privacidad publicados (los exige MP/Flow y el SII) | B2, legal | 🟡 |
| B8 | Confirmar billing limits de OpenAI/Gemini para producción (hoy soportan el flujo actual) | escala | 🟢 |
| B9 | Primeros 3-5 restaurantes beta para validar el cobro real | go-to-market | 🟢 |

## 4. Secuencia propuesta (2-3 semanas a facturación)

1. **Semana 1**: B1 + B2 en paralelo con C1, C4, C6. Apenas lleguen keys → C2.
2. **Semana 2**: C3 (sandbox E2E) + B3 (SII) + C5/C9/C10. **Primer cobro de prueba real.**
3. **Semana 3**: C7 (pago en conversación) + C8 + B9 (betas pagando).

## 5. Ya hecho (no repetir)

- Registro formulario clásico + wizard onboarding — DEPLOYED y verificado E2E (2026-06-11).
- Stripe SaaS backend+frontend completo (queda como vía internacional).
- Fix 403 `LeadReader` para callback_manual/tasks — DEPLOYED.
