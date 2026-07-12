# Sudamérica AI Backend

Backend FastAPI multi-servicio para `api_execute`, `callback_manual`, `tasks`, `canales_service` y `open_agent`.

## Canonical tenancy

- La convencion vigente es `tenant_id`.
- El claim JWT vigente es `tenant_id`.
- El header operativo vigente es `X-Tenant-ID`.
- El contexto RLS vigente es `current_setting('app.current_tenant_id')`.
- No existe una segunda convencion de tenancy en runtime.

## Schema ownership

- Alembic es la fuente de verdad para evolucionar el esquema.
- `infra/001_schema.sql`, `infra/002_rls_policies.sql` y `infra/003_indexes.sql` son un snapshot legible del estado esperado.
- `init_db.sql` sirve solo para bootstrap de una base vacia; incluye `infra/*` y datos demo.
- `init_db.py` aplica `alembic upgrade head` al `DATABASE_URL` configurado.

## Active services

| Servicio | Puerto | Responsabilidad |
|----------|--------|-----------------|
| `api_execute` | 8000 | Auth, tenants, usuarios, catalogo, leads, ventas, metricas, Stripe, alertas, sales targets, orquestacion IA (config, conversaciones, knowledge) |
| `callback_manual` | 8002 | Revision humana de respuestas IA |
| `tasks` | 8003 | Entrega async y auditoria de envios |
| `canales_service` | 8004 | Instancias Evolution, WhatsApp, QR y webhooks |
| `open_agent` | 8005 | Generacion de texto LLM (`POST /api/v1/agent/generate`) |

## Tables

### Global tables

- `tenants`: tabla raiz compartida; no lleva `tenant_id`.
- `stripe_events`: log global de idempotencia de webhooks Stripe. Se mantiene global porque el `stripe_event_id` es unico a nivel cuenta y algunos eventos deben deduplicarse antes de resolver el tenant desde el payload.
- `alembic_version`: control interno de migraciones.

### Tenant-scoped tables

- `usuarios`
- `categorias`
- `productos`
- `leads`
- `ventas`
- `agente_config`
- `revision_humana`
- `ai_conversations`
- `ai_embeddings`
- `smart_alerts`
- `sales_targets`
- `evolution_instances`
- `llm_provider_keys`
- `task_logs`

Todas las tablas tenant-scoped deben tener `tenant_id`, RLS `ENABLE`, RLS `FORCE` y policy `tenant_isolation`.

## Local setup

```bash
cd backend
python -m pip install -r requirements.txt
python run_alembic.py upgrade head
pytest -q api_execute/tests/test_alertas.py api_execute/tests/test_sales_targets.py callback_manual/tests/test_revision.py tasks/tests/test_send_response.py canales_service/tests/test_bootstrap.py
```

## Notes

- `canales_service` ya no crea tablas en runtime; exige que `evolution_instances` exista via Alembic.
- `task_logs` es tenant-scoped y queda bajo RLS.
- `revision_humana` mantiene el patron de `TenantBase`; la columna `activo` forma parte del esquema esperado.
