# Fase B — Manifiesto de rubro en tabla BD + versión + anclaje (Paso 5)

> Nota de diseño del Paso 5. Continúa la Fase A (`fase-A-manifiesto.md`). Alcance:
> **persistir** el manifiesto de rubro en una tabla BD global, servirlo en runtime desde un
> **registro con caché en proceso** (sin volver `async` las funciones puras), permitir
> **editarlo en runtime** vía un CRUD de admin de plataforma con **validación fail-closed**, y
> **anclar la versión del manifiesto por conversación** para que una edición en vuelo no altere
> una conversación ya iniciada. Todo en LOCAL, sin tocar GCP. Deja **restaurante byte-idéntico**
> y la paridad py↔ts del Paso 4 intacta.
>
> **Fuera de alcance (→ Paso 6+):** i18n/multi-moneda (se mantiene es-ES/CLP), sub-agentes por
> rubro, rename de esquema `mesas→recursos`/`comandas`, y creación de rubros nuevos por `POST`
> (el CRUD de Fase B **edita** rubros existentes; el roster de claves se mantiene invariante).

## 0. Re-verificación contra el repo actual (anchors del §3 del prompt)

Cada anchor re-verificado por `grep`/lectura sobre la rama `paso5-manifiesto-bd` (base
`paso4-kernel-multirubro`, HEAD `3774a83`):

- **Manifiesto solo en código, sin BD, sin versión:** `backend/shared/rubros/diccionario.py`
  (3304 líneas): `Rubro` es `@dataclass(frozen=True)` (línea 55); `_RUBROS: dict[str, Rubro]`
  (línea 114); `rubros_disponibles`/`rubro_def`/`resolve_rubro`/`get_rubro` (líneas 3277–3304),
  **síncronas y puras**. `RUBRO_DEFAULT = "restaurante"`. **No existe tabla `rubros`**
  (`grep` en `infra/` = 0). Único dato persistido del rubro: `tenants.config["rubro"]` (JSONB),
  validado en publicación por el Paso 4 (`schemas/tenant_config.py`).
- **Export canónico (Paso 4):** `backend/shared/rubros/export_manifest.py` → `build_manifest()`
  (claves `rubro_default`, `primitivas`, `capacidades`, `rubros{}`) → fixture
  `frontend/lib/__fixtures__/rubros.manifest.json` (104 KB, 101 rubros). Ese fixture es la
  **verdad-py** que `frontend/lib/rubros.parity.test.ts` (104 tests) verifica contra el espejo ts.
- **Contrato validado (Paso 4):** `RubroManifest` en `schemas/tenant_config.py` (pydantic,
  `extra='forbid'`, valida labels completos por `PRIMITIVAS`). Fase B **reusa** este contrato
  para la escritura del CRUD.
- **Entrada del rubro al flujo:** `api_execute/app/services/tenant_rubro.py::load_tenant_rubro`
  devuelve la **clave** (fail-safe `restaurante`, loggeado); los consumidores llaman después
  `rubro_def(clave)` para obtener el `Rubro`. Consumidores verificados: `ai_orchestrator`,
  `sudamerica_orchestrator`, `rubro_prompt`, `prompt_sections`, `prompts_ai`, `comanda_svc`,
  `mesa_svc`, `menu_import_svc`, `subentidades`, `loyalty_outreach`, `auth_service`.
- **Plantilla de tabla GLOBAL:** `api_execute/app/models/platform_config.py` (`key` único,
  `value` JSON, `updated_at`, `updated_by` FK a `usuarios`); DDL en `infra/001_schema.sql:417`.
  **Sin** policy `tenant_isolation` (global; authz de escritura en app-layer,
  `routes/admin_system.py` + `services/admin_service.py::upsert_platform_config`, scope
  `SuperAdminOnly`).
- **Sesión/conversación:** `sessions` (`infra/001_schema.sql:192`) tiene `id`, `tenant_id`,
  `channel`, `status`, `manifest_version` (nuevo). **Hallazgo:** el flujo de chat vivo **NO
  crea filas en `sessions`** (`grep` de `INSERT INTO sessions` en la app = 0). La persistencia
  por-turno vive en `ai_conversations` (`:208`, `session_id` **nullable**), y "conversación" es
  una agregación por `lead_id`/`session_id`. → **El anclaje efectivo se hace por el primer turno
  persistido** (ver §4), no por la creación de una fila `sessions`. `sessions.manifest_version`
  se añade igualmente por contrato y para los flujos futuros basados en sesión.
- **Última migración:** `infra/027_fix_public_rls.sql` → esta fase crea `028`.

## 1. Esquema de la tabla `rubros` (global, sin `tenant_id`)

Migración `infra/028_rubros_manifest.sql`. Columnas = espejo del `RubroManifest`:

| columna | tipo | fuente `RubroManifest` |
|---|---|---|
| `key` | `VARCHAR(80)` **PK** | `key` |
| `nombre` | `TEXT NOT NULL` | `nombre` |
| `emoji` | `TEXT NOT NULL` | `emoji` |
| `sector` | `TEXT NOT NULL` | `sector` |
| `labels` | `JSONB NOT NULL` | `labels` (12 primitivas → label) |
| `capacidades` | `JSONB NOT NULL` | `capacidades` (lista, orden CAP_ORDER) |
| `sub_entidad_label` | `TEXT NULL` | `sub_entidad_label` |
| `recurso` | `BOOLEAN NOT NULL DEFAULT FALSE` | `recurso` |
| `variantes` | `BOOLEAN NOT NULL DEFAULT TRUE` | `variantes` |
| `precio_medida` | `BOOLEAN NOT NULL DEFAULT FALSE` | `precio_medida` |
| `categorias_semilla` | `JSONB NOT NULL DEFAULT '[]'` | `categorias_semilla` |
| `version` | `INT NOT NULL DEFAULT 1` | por-fila: se incrementa en cada edición |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | — |
| `updated_by` | `UUID NULL REFERENCES usuarios(id)` | — |

- **No lleva `tenant_isolation`** (es tabla de referencia global, sin `tenant_id`): no hay
  superficie cross-tenant que aislar. La ESCRITURA es solo de admin de plataforma (app-layer),
  igual que `platform_config`. Se documenta en la migración.
- **Contador global de versión del manifiesto** (`manifest_version`): default §10.3 = fila en
  `platform_config` con clave `rubro_manifest_version` (`value = {"version": <int>}`). Reusa el
  mecanismo global existente; evita una tabla singleton nueva. El seed lo inicializa en `1`.
- `sessions` gana `manifest_version INT NULL`; `ai_conversations` gana `manifest_version INT
  NULL` (portador runtime del anclaje por-turno; ver §4). Ambos nullable: `NULL` ⟺ no anclado
  → se resuelve a la versión vigente, loggeado.

## 2. Seed reproducible (node ← fixture)

El host **no** trae `python`/`docker`; `node` sí. El seed se genera con node para garantizar
`seed == verdad-py` sin ejecutar python:

- `tools/gen_rubros_seed.mjs` lee el FIXTURE (`frontend/lib/__fixtures__/rubros.manifest.json`,
  ya commiteado y guardado por `rubros.parity.test.ts`) y emite un **UPSERT idempotente**
  determinista a `infra/029_rubros_seed.sql`: un `INSERT ... ON CONFLICT (key) DO UPDATE` por
  rubro (orden alfabético por clave, igual que el fixture) + el `UPSERT` de la fila
  `rubro_manifest_version` en `platform_config` a `1`.
- Como el fixture **deriva de `diccionario.py`** (`export_manifest.py`) y el seed **deriva del
  fixture**, hay **una sola verdad**: `diccionario.py ⇒ fixture ⇒ seed`.
- **Test anti-drift** (`vitest`): `frontend/lib/rubros.seed.test.ts` regenera el SQL en memoria
  desde el fixture (reusando el mismo módulo que `gen_rubros_seed.mjs`) y lo compara byte a byte
  con `infra/029_rubros_seed.sql` commiteado → cualquier drift (fixture editado sin regenerar el
  seed, o seed editado a mano) **falla**. El test de paridad del Paso 4 sigue intacto.
- El seed entra en la cadena local `infra/[0-9]*.sql` que `init-local-db.sh` aplica en orden
  (`backend/LOCAL_DEV.md`).

## 3. Registro con caché en proceso (`services/rubro_registry.py`)

Módulo nuevo en `api_execute`. **No** cambia la firma de ninguna función de `shared/rubros`.

- **Estado (módulo-global):** `_current: dict[str, Rubro]` (caché vigente), `_version: int`
  (versión vigente), y `_snapshots: OrderedDict[int, dict[str, Rubro]]` **acotado** (últimas
  `_MAX_SNAPSHOTS = 16` versiones) para el anclaje.
- **Carga/refresh** (`async load(db)` / `async refresh(db)`): `SELECT` de `rubros` → construye
  `dict[str, Rubro]` (mismo dataclass, `labels` a `MappingProxyType`, `capacidades`/`semillas`
  a tuplas) y lee `manifest_version` de `platform_config`. Se llama en el `lifespan` de la app
  y tras cada escritura del CRUD. **Fallback fail-safe loggeado** a `diccionario._RUBROS` (y
  versión `0`) si la tabla está vacía/indisponible o la carga falla. Guarda el snapshot de la
  versión cargada en `_snapshots`.
- **Accesores SÍNCRONOS** (equivalentes a los de `diccionario`, leídos del caché):
  - `rubro_def(key)` — resuelve la versión efectiva = `_anchor.get()` (ContextVar, §4) o
    `_version`; elige el snapshot de esa versión (si la versión anclada expiró del caché
    acotado → cae a `_current` **loggeando** la deriva); devuelve el `Rubro`, con fail-safe a
    `restaurante` idéntico a `diccionario.rubro_def`. **Si el caché está vacío → delega en
    `diccionario.rubro_def`** (fallback puro).
  - `resolve_rubro(config)` / `rubros_disponibles()` — envuelven el roster del caché con
    fallback a `diccionario`. Como `seed roster == diccionario roster`, el comportamiento es
    idéntico hoy; quedan listos para un `POST` de rubro futuro (Paso 6).
- **Invariante clave:** con la tabla seedeada, `registry.rubro_def(k)` produce un `Rubro`
  **idéntico** a `diccionario.rubro_def(k)` para toda clave (test `seed↔código`). Por eso
  **restaurante es byte-idéntico**: el registro solo diverge de `diccionario.py` tras una
  edición de admin.
- **Repunte de consumidores:** los módulos de runtime que hoy hacen
  `from shared.rubros import rubro_def` pasan a `from app.services.rubro_registry import
  rubro_def` (swap de import, misma firma, mismo tipo de retorno): `ai_orchestrator`,
  `sudamerica_orchestrator`, `rubro_prompt`, `prompt_sections`, `prompts_ai`, `comanda_svc`,
  `mesa_svc`, `menu_import_svc`, `subentidades`, `loyalty_outreach`, `auth_service`.
  `tenant_rubro.load_tenant_rubro` pasa a resolver la clave con
  `registry.resolve_rubro`/`rubros_disponibles` (roster invariante hoy; correcto si mañana hay
  `POST`). `shared/rubros` **no cambia**: sigue como fuente de autoría, fallback y oráculo.

## 4. CRUD admin de rubro (validación fail-closed) — `routes/admin_rubros.py`

Router nuevo `admin_rubros` (prefijo `/rubros`, montado en `/api/v1/admin` → `/api/v1/admin/rubros`),
mismo patrón que `admin_system`: `SuperAdminOnly` + `get_db_admin`. Lógica en `admin_service.py`.

- `GET /admin/rubros` — lista todos los rubros de la tabla.
- `GET /admin/rubros/{key}` — un rubro (404 si no existe).
- `PATCH /admin/rubros/{key}` — edita `labels`/`capacidades`/`sub_entidad_label`/flags en
  runtime. Cada escritura:
  1. **Valida** el manifiesto resultante contra `RubroManifest` (fail-closed **422** reusando el
     Paso 4). Se **refuerza** `RubroManifest` con un validador que rechaza `capacidades`
     desconocidas (fuera de `CAPACIDADES`) — labels incompletos o capacidad desconocida ⇒ 422.
     La tabla nunca queda en estado inválido.
  2. Persiste la fila, incrementa `rubros.version` de esa fila.
  3. **Bumpea** el contador global `rubro_manifest_version` (`platform_config`).
  4. Llama `registry.refresh(db)` para servir la nueva definición de inmediato (sin redeploy).
- La escritura es **solo de plataforma** (`SuperAdminOnly`), **nunca** de tenant. El override
  por-tenant sigue siendo `tenant.config` (ya cubierto), no entra aquí (§10.4 default).
- Crear rubro nuevo (`POST`) queda **fuera de alcance** (roster invariante en Fase B).

## 5. Anclaje de versión por conversación

**Objetivo:** una edición del manifiesto en vuelo **no** altera una conversación ya iniciada;
solo afecta conversaciones nuevas.

- **Mecanismo:** ContextVar `_anchor` en el registro. En el punto de entrada del mensaje de
  **cliente** (`ai_orchestrator.orchestrate_chat`, tras detectar mesa/canal y antes de componer)
  se determina la **versión anclada** (`_resolve_manifest_anchor`) y se envuelve **toda** la
  composición del prompt con `with anchored(version):`. Así cada consumidor repunteado
  (`build_system_message`, `welcome_rules_whatsapp`, `_build_mesa_prompt_section`) ve el mismo
  snapshot, **sin** cambiar ninguna firma. El **copiloto admin** (`sudamerica_orchestrator`) usa
  la versión **vigente** por diseño: es platform-side y single-user (el propio admin que edita el
  manifiesto), por lo que "no alterar una conversación en vuelo" no es un requisito de corrección
  ahí — el admin espera ver sus ediciones de inmediato.
- **Dónde se estampa (el flujo vivo no crea `sessions`):** el anclaje efectivo es por **primer
  turno persistido**. Al procesar un mensaje:
  - Se consulta el `manifest_version` del turno más antiguo de la conversación (por
    `lead_id`/`session_id` en `ai_conversations`).
  - Si existe (no es el primer turno) → versión anclada = ese valor.
  - Si no existe (primer turno) → versión anclada = `registry.current_version()`.
  - Cada turno se persiste con `ai_conversations.manifest_version = <versión anclada>`, de modo
    que el primer turno fija el ancla y los siguientes lo heredan.
- **`sessions.manifest_version`** se añade por contrato: cuando un canal cree filas `sessions`,
  se estampa la versión vigente en la creación y esa columna tiene prioridad sobre el
  "primer turno". Hoy ningún canal la escribe → se documenta y se usa el fallback por-turno.
- **Expiración del snapshot:** si la versión anclada ya no está en el caché acotado
  (`_MAX_SNAPSHOTS`), `rubro_def` cae a la versión vigente **loggeando** la deriva (§10.2
  default: caché acotado, no snapshots persistidos arbitrariamente viejos).

## 6. Invariantes (del Registro §4 del diagnóstico)

- **K:** aislamiento RLS `tenant_isolation` intacto (tablas tenant no se tocan; `rubros` es
  global y no introduce superficie cross-tenant); AuthN/AuthZ de plataforma (escritura de rubro
  solo `SuperAdminOnly`); jerarquía **Kernel > tenant > rubro** (un manifiesto editado NO pisa
  los guardrails del kernel — el CRUD solo toca labels/capacidades/flags del rubro, no las
  reglas del kernel).
- **Una sola verdad:** `diccionario.py` (código, autoría, fallback) ⇒ fixture (verdad-py,
  paridad) ⇒ seed (BD). Tests detectan divergencia entre las tres (paridad + seed↔fixture +
  seed↔código).
- **Restaurante byte-idéntico** es la prueba de no-regresión.

## 7. Verificación (sin python/docker en host)

- **Frontend:** `npm run typecheck && npm run test` verdes, incl. (a) paridad del Paso 4
  intacta y (b) nuevo `rubros.seed.test.ts` (drift seed↔fixture falla).
- **Backend por lectura:** el registro carga de la tabla con fallback loggeado; `seed↔código`
  idéntico (verificado componiendo el `Rubro` desde el fixture y comparándolo con el esperado);
  restaurante byte-idéntico (el registro vacío delega en `diccionario`, y seeded == diccionario);
  CRUD valida fail-closed; anclaje estampa y resuelve por versión. Se documenta explícitamente lo
  no ejecutable (pytest/uvicorn/alembic requieren python/docker ausentes).
- **Oráculo seed↔código (test):** `api_execute/tests/test_rubro_registry.py` reconstruye cada
  `Rubro` desde el fixture con la MISMA lógica del registro (`_row_to_rubro`) y lo compara con
  `diccionario.rubro_def(k)`. Cierra el eslabón **fixture↔código** de la cadena (los otros dos ya
  guardados: `rubros.seed.test.ts` seed↔fixture, `rubros.parity.test.ts` fixture↔espejo-ts) → una
  divergencia entre las tres proyecciones falla en CI. No requiere BD (corre bajo pytest, ausente
  en este host; se validó por lectura que las claves del fixture == las que `_row_to_rubro` lee).
- **RLS:** `grep 'USING (true)'` en policies vivas = 0 (Paso 4); `rubros` global sin superficie
  cross-tenant.

## 8. Revisión adversarial (Paso 5, bloque F)

Seis lentes; ningún defecto de código sobreviviente (el único hueco —fixture↔código sin test— se
cerró con `test_rubro_registry.py`):

1. **compat-restaurante:** el seed de `restaurante` deriva del fixture que deriva de
   `diccionario.py`; `_row_to_rubro` reconstruye un `Rubro` igual por valor (labels a
   `MappingProxyType`, capacidades/semillas a tuplas en orden CAP_ORDER). Con el registro vacío,
   `rubro_def` delega en `diccionario` → idéntico. **Byte-idéntico.**
2. **paridad py↔ts:** fixture intacto; el seed deriva de él; `rubros.parity.test.ts` (104) verde.
3. **una sola verdad:** las tres proyecciones (código⇒fixture⇒seed) quedan guardadas por tests
   encadenados (ver §7). El seed no puede divergir del fixture ni el fixture del código sin fallo.
4. **aislamiento/seguridad:** el CRUD es `SuperAdminOnly` (nunca tenant); `rubros` es global sin
   `tenant_id` → sin superficie cross-tenant; el registro solo mapea clave→definición (vocabulario
   global), la clave del tenant sigue en `tenant.config` (RLS). RLS `USING(true)` = 0.
5. **anclaje coherente:** el primer turno fija la versión vigente; los siguientes heredan el ancla
   del turno más antiguo. Tras un bump de admin, la conversación en vuelo sirve su snapshot
   (caché acotado; fallback-a-vigente loggeado si expiró) → **una edición en vuelo no la altera.**
6. **fallback:** carga en `lifespan`, `refresh` y `rubro_def` con fail-safe loggeado a
   `diccionario._RUBROS`; BD caída al arrancar ⇒ la app arranca y sirve desde código, sin crash.
