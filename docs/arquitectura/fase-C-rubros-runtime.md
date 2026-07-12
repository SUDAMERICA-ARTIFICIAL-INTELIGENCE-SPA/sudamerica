# Fase C — Roster de rubros en runtime: crear + ciclo de vida (Paso 6)

> Nota de diseño del Paso 6. Continúa la Fase B (`fase-B-manifiesto-bd.md`). Alcance: el manifiesto
> de rubro pasa de **editable** (Paso 5) a **extensible**. Un admin de plataforma puede **crear**
> un rubro nuevo en runtime (`POST /admin/rubros`, validado fail-closed, sin redeploy) y
> **gestionar su ciclo de vida** (activar/desactivar). Se introduce por primera vez una **clase de
> rubro que vive SOLO en BD** (`origen='runtime'`), claramente separada de los rubros
> `origen='seed'` (proyección byte-idéntica de `diccionario.py`, invariante y test-guarded). Todo
> en LOCAL, sin tocar GCP. Deja **restaurante byte-idéntico** y la paridad py↔ts / el sync
> seed↔fixture del Paso 4/5 intactos (siguen cubriendo solo el roster de código).
>
> **Fuera de alcance (→ Paso 7+):** rename de esquema `mesas→recursos`/`comandas`, sub-agentes
> conversacionales por rubro, e i18n/multi-moneda (se mantiene es-ES/CLP). La Fase C deja el
> roster **extensible en runtime** — base para poblar esos rubros nuevos en pasos siguientes.

## 0. Re-verificación contra el repo actual (anchors del §3 del prompt)

Re-verificado por `grep`/lectura sobre la rama `paso6-rubros-runtime` (base `paso5-manifiesto-bd`,
HEAD `cb4b437`):

- **Tabla `rubros` (Paso 5):** `backend/infra/028_rubros_manifest.sql` crea `rubros` global
  (`key` PK, sin `tenant_id`, sin RLS; `version` INT por-fila, `updated_at/by`). Seed idempotente
  en `029_rubros_seed.sql` (generado por `tools/gen_rubros_seed.mjs` + `tools/rubros-seed.mjs`
  desde el fixture; `INSERT ... ON CONFLICT (key) DO UPDATE`). **Última migración = `029` → se crea
  `030`.**
- **Registro con caché (Paso 5):** `api_execute/app/services/rubro_registry.py` carga la tabla a
  `dict[str, Rubro]` en el `lifespan`, cachea `manifest_version`, expone `rubro_def`/`resolve_rubro`/
  `rubros_disponibles` **síncronos**, `refresh()` tras escrituras, y **fallback loggeado** a
  `diccionario._RUBROS` si la tabla está vacía/indisponible. Anclaje por conversación vía
  ContextVar + `_snapshots` acotado (`_MAX_SNAPSHOTS=16`).
- **CRUD admin (Paso 5, solo GET/PATCH):** rutas en `routes/admin_rubros.py` (no en
  `admin_system.py` como decía el prompt); lógica en `services/admin_service.py`
  (`list_rubros`/`get_rubro`/`update_rubro`); schema en `schemas/admin_rubros.py`. Cada `PATCH`
  valida contra `RubroManifest`, **bumpea `manifest_version`** (`_bump_manifest_version`) y llama
  `registry.refresh()`. **No existía `POST`** de rubro ni columna de estado/origen.
- **Validación reusable (Paso 4):** `RubroManifest` (`schemas/tenant_config.py`, `extra='forbid'`,
  labels completos por `PRIMITIVAS`, capacidades por `CAPACIDADES`). `validate_tenant_config` →
  422. La publicación (`TenantConfig`) validaba el `rubro` contra `shared.rubros.rubros_disponibles()`
  (roster **estático**) — insuficiente para asignar un rubro runtime; se corrige en la Fase C.
- **Fixture y paridad:** `frontend/lib/rubros.parity.test.ts` (fixture ↔ espejo ts) y
  `frontend/lib/rubros.seed.test.ts` (fixture ↔ `029.sql`). **Ninguno consulta la BD**: por
  construcción cubren solo el roster de código.

## 1. Dos clases de rubro, una sola verdad POR CLASE

| | `origen='seed'` | `origen='runtime'` |
|---|---|---|
| Autoría | `shared/rubros/diccionario.py` | Admin vía `POST /admin/rubros` |
| Dónde vive | código ⇒ fixture ⇒ seed ⇒ BD | **solo BD** |
| Cadena "una sola verdad" | sí (test-guarded, byte-idéntica) | **exento** (sin código, sin fixture, sin fallback de código) |
| Membresía | **inmutable** (no se crea/retira; solo se edita por el `PATCH` del Paso 5) | ciclo de vida (activar/desactivar) |
| Fallback (BD caída) | reconstruido desde `diccionario._RUBROS` | cae a `RUBRO_DEFAULT` loggeado (§4) |

El test seed↔fixture **solo** cubre filas `origen='seed'` (de hecho, solo compara el `.sql` 029 con
el fixture); un rubro runtime NO cuenta como divergencia. `restaurante` (seed) sigue siendo el
oráculo de no-regresión: byte-idéntico a `_RUBROS["restaurante"]`.

## 2. Esquema — migración `030_rubros_lifecycle.sql`

Añade a `rubros` (idempotente, `ADD COLUMN IF NOT EXISTS`):

- `origen VARCHAR(10) NOT NULL DEFAULT 'seed' CHECK (origen IN ('seed','runtime'))`.
- `activo BOOLEAN NOT NULL DEFAULT TRUE`.
- Índice parcial `ix_rubros_activo ON rubros (activo) WHERE activo`.

**Backfill implícito:** las filas seedeadas por 029 quedan `origen='seed'`, `activo=true` por
DEFAULT. La 030 **no toca el contenido del seed** (el `ON CONFLICT DO UPDATE` de 029 no menciona
`origen`/`activo` ⇒ re-seedear los preserva) → restaurante byte-idéntico. `origen` es **inmutable**
tras crear (el CRUD nunca lo expone como editable; fail-closed en app-layer). `rubros` sigue global
(sin `tenant_isolation`).

## 3. `POST /admin/rubros` — crear rubro runtime (`admin_service.create_rubro`)

Solo admin de plataforma (`SuperAdminOnly`). Reglas fail-closed (la tabla nunca queda inválida):

1. **key bien formada** (`^[a-z][a-z0-9_]{2,79}$`): inválida ⇒ **422**.
2. **key no reservada:** rechaza (**409**) si la key pertenece al **namespace de código** —el roster
   de `diccionario.py` (`_code_roster()`)— o si ya existe en la tabla (seed o runtime). Regla de key
   reservada: el dueño autoritativo de una key de código es siempre `diccionario.py`; este chequeo +
   la unicidad de la PK impiden que un runtime ensombrezca un rubro de código (presente o futuro).
3. **manifiesto válido** contra `RubroManifest` (labels completos + capacidades del enum): inválido
   ⇒ **422**. Un rubro runtime NO puede inventar capacidades/primitivas fuera del enum
   (`Kernel > tenant > rubro`).
4. Persiste `origen='runtime'`, `activo=true`, `version=1`; **bumpea `manifest_version`**;
   `registry.refresh()`.

## 4. Ciclo de vida — activar/desactivar (`admin_service.set_rubro_activo`)

`POST /admin/rubros/{key}/desactivar` y `/{key}/activar`. Solo sobre `origen='runtime'`:

- Un rubro **seed** no puede desactivarse (**409**): su membresía es la del roster de código.
- **`RUBRO_DEFAULT` nunca** se desactiva (409, defensa redundante — es seed).
- **Guardrail de uso (§10.2 default = reject):** desactivar un rubro asignado a ≥1 tenant
  (`tenants.config->>'rubro' = key`) se rechaza (**409**) con la lista de tenants afectados (no se
  dejan huérfanos). No hay `?force`.
- No-op idempotente si el estado ya es el pedido (no bumpea). Cada cambio efectivo bumpea
  `manifest_version` + `refresh()`.

**Hard-delete:** fuera de alcance (§10.1 default = soft). No hay `DELETE` físico; desactivar deja la
fila para preservar el snapshot de conversaciones ancladas.

## 5. Registro — unión seed+runtime, fallback solo-seed

`rubro_registry.refresh()` carga `SELECT ... FROM rubros WHERE activo = TRUE` → `_current` con la
unión de seed+runtime activos. `rubros_disponibles()` devuelve sus claves; `rubro_def`/`resolve_rubro`
sirven ambas clases. **Sin cambio de firma** (siguen síncronas y puras).

- **Fallback fail-safe** (BD caída/vacía): `_current` queda `{}` → los accesores delegan en
  `diccionario` (roster **solo-seed**; los runtime no tienen fuente de código). Un tenant cuyo
  `rubro` es runtime, con BD indisponible, resuelve a `RUBRO_DEFAULT`; el aviso loggeado lo emite
  `tenant_rubro.load_tenant_rubro` (que compara la clave cruda con la resuelta). Fail-safe, no crash.
- **Anclaje (Paso 5 intacto):** crear/activar/desactivar bumpea la versión; una conversación anclada
  a una versión previa sigue viendo su snapshot (incluida la que usa un rubro runtime luego
  desactivado) hasta que esa versión expire del caché acotado.

## 6. Publicación acepta runtime — `TenantConfig`

`schemas/tenant_config.py::_rubros_conocidos()` valida el `rubro` de un tenant contra el **set vivo**
del registro (`rubro_registry.rubros_disponibles()`, unión seed+runtime activos) para que un tenant
pueda asignarse un rubro runtime. Import perezoso + fallback al roster de código si el registro no
está cargado (arranque / tests sin BD) → los tests del Paso 4/5 siguen validando contra el roster
estático sin cambios.

## 7. Descubrimiento por API + frontend

- **Backend:** `GET /api/v1/core/rubros/disponibles` (público, `routes/rubros.py` +
  `schemas/rubros_publicos.py`) sirve el set vivo (seed+runtime activos, con labels/capacidades)
  desde el caché del registro (sin round-trip a BD; fallback puro al roster de código).
- **Frontend:** `lib/rubros-live.ts` (`fetchRubrosDisponibles` + `mergeRubroOptions`) y el hook
  `hooks/useRubrosDisponibles.ts` fusionan el set vivo sobre el baseline estático (`RUBRO_OPTIONS`).
  El baseline se conserva si la API falla (fail-open). El selector de `register/page.tsx` lo consume.
  **El fixture sigue siendo el *baseline de código*; la API es la *fuente de verdad del set vivo*.**
  La paridad py↔ts y el sync seed↔fixture NO se debilitan (cubren solo el roster de código).

## 8. Invariantes (no romper)

- **Restaurante byte-idéntico** (la 030 no toca el seed) — prueba de no-regresión.
- **Una sola verdad por clase:** seed = `diccionario.py`⇒fixture⇒seed con test que detecta drift;
  runtime = solo BD, exento y sin fallback de código.
- **Membresía del roster seed inmutable:** no se crea key que colisione con seed; no se
  desactiva/borra un seed; `RUBRO_DEFAULT` nunca se desactiva.
- **RLS / aislamiento:** `rubros` global sin superficie cross-tenant; la escritura (crear/activar/
  desactivar) es solo admin de plataforma, nunca tenant. `Kernel > tenant > rubro`.

## 9. No ejecutable en el host (documentado)

`python`/`docker` no existen en el host: no se pudieron correr `pytest`/`alembic`/`uvicorn`/
`docker compose`. El backend se verifica por **lectura** y por los tests **frontend** (`vitest`),
que sí cubren los invariantes de datos (030, sync acotado a seed, fusión del set vivo). La cadena
de migraciones (incl. `030`) la aplica `init-local-db.sh` cuando haya Docker.
