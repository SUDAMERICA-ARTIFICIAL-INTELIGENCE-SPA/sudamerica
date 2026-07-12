# Arranque local (Docker Compose) — sin GCP

Stack local: `postgres` + `api-execute` (:8000) + `open-agent` (:8005) +
`callback-manual` (:8002) + `tasks` (:8003) + `canales-service` (:8004) +
`gateway` (nginx :80). No se despliega nada a GCP.

> Verificado por **lectura** en este entorno: aquí no hay `docker` ni `python`,
> así que los comandos de abajo no se ejecutaron. Los `.env` y el esquema de init
> sí quedaron creados y su coherencia se validó (ver §Notas).

## 1. Secretos (.env) — ya creados, gitignored

Se generaron los `.env` de cada servicio (raíz + api_execute, open_agent,
canales_service, callback_manual, tasks) con:

- `DATABASE_URL=postgresql+asyncpg://sudamerica:<pass>@postgres:5432/sudamerica_ai`
  (host `postgres`, DB `sudamerica_ai`; `open_agent` no usa BD).
- **Un mismo `JWT_SECRET_KEY`** (64 hex) en los 5 servicios.
- **5 claves internas distintas** (una por servicio, ≥32 bytes), y en cada `.env`
  las claves de los pares que ese servicio confía (según el trust map de su
  `config.py`). Todas únicas → cumple `_check_key_uniqueness`.
- `POSTGRES_PASSWORD` (rotada) vive en `backend/.env`; `docker-compose.yml` la lee
  como `${POSTGRES_PASSWORD}` (no se commitea ningún secreto).
- Claves LLM (`OPENAI_API_KEY`/`GEMINI_API_KEY`) vacías: el arranque/health NO las
  necesita; la generación real de chat SÍ (ponlas para probar el LLM).

Si faltara algún `.env`, recréalos desde su `.env.example` respetando esas reglas.

## 2. Levantar Postgres + esquema

En el **primer** init de un volumen `pgdata` vacío, `infra/init-local-db.sh`
(montado como `000_init-local-db.sh`) aplica **toda** la cadena `infra/[0-9]*.sql`
en orden. Esto es necesario porque hay columnas que el código lee y que NO están
en 001/002/003 — p.ej. `agente_config.debounce_seconds` (solo en `infra/012`, y
ausente del historial de alembic). Los `.sh`/`README`/`PRE_DEPLOY.md` de `infra/`
se ignoran (el glob es `[0-9]*.sql`).

```bash
cd backend
docker compose up -d postgres
docker compose logs -f postgres   # espera "database system is ready to accept connections"
```

Si ya habías levantado postgres con la contraseña vieja, reinicia el volumen para
re-aplicar el esquema y tomar la nueva password:

```bash
docker compose down -v && docker compose up -d postgres
```

> No hace falta `alembic upgrade head`: el esquema local canónico es la cadena
> `infra/*.sql` completa, que ya incluye lo que alembic no tiene.

## 3. Levantar el resto y verificar health

```bash
docker compose up -d
curl -fsS localhost:8000/health && echo        # api_execute
for p in 8002 8003 8004 8005; do curl -fsS localhost:$p/health && echo; done
```

## 4. Frontend

`frontend/.env.local` ya apunta cada `NEXT_PUBLIC_API_*` a su puerto local y **no**
define `NEXT_PUBLIC_API_DIALER` (el target `dialer` resuelve a api_execute en
`/api/v1/core/ai`). El WebSocket está desactivado (el visor refresca por polling).

```bash
cd frontend && npm run dev    # http://localhost:3000
```

## 5. Smoke test end-to-end (documentado)

Un mensaje entrante (o mock de Evolution) recorre
`canales_service → api_execute → open_agent /api/v1/agent/generate → respuesta
persistida en ai_conversations`; el dashboard lo ve en
`GET /api/v1/core/ai/conversations`. Requiere una clave LLM real en
`api_execute/.env` + `open_agent/.env` para que la generación no degrade.

## Notas

- Coherencia de `.env` validada por lectura: password de BD idéntica en
  `backend/.env` y en los 4 `DATABASE_URL`; `JWT_SECRET_KEY` idéntico en los 5;
  cada clave interna con un único valor dondequiera que aparece; 5 valores
  globalmente distintos.
- No ejecutado aquí por falta de `docker`/`python` en el host.
