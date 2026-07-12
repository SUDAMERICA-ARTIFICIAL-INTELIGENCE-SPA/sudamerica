# Fase A — Kernel multi-rubro por manifiestos (Paso 4)

> Nota de diseño del Paso 4. Alcance: convertir "la verdad del rubro" de código
> duplicado sin validar en un **manifiesto de fuente única, validado en publicación y
> con paridad py↔ts garantizada por test**, y cerrar las fugas restaurante-céntricas de
> alto impacto **dejando restaurante byte-idéntico**. Todo en LOCAL, sin tocar GCP.
> La persistencia del manifiesto en tabla BD, el anclaje de versión, i18n/multi-moneda y
> los sub-agentes por rubro son **Paso 5**.

## 0. Re-verificación contra el repo actual (sin `MVP/`, sin `AI_dialer`)

El diagnóstico (`fase1-diagnostico.md`) se escribió contra el viejo monorepo `MVP/`. Se
re-verificó cada hallazgo §3.A/§3.C/§3.D/§3.E contra este repo:

- **§3.A (prompts):** vigente. Rutas reubicadas (sin `MVP/`): `api_execute/app/services/prompt_sections.py`,
  `api_execute/app/prompts_ai.py`, `api_execute/app/services/loyalty_outreach.py`,
  `api_execute/app/services/comanda_notify.py`. El chat pasa por `open_agent`, no `AI_dialer`.
- **§3.C (tools):** vigente en `open_agent/app/services/tools.py` (28 tools planas) + `agent_engine.py`.
- **§3.D (RLS):** **parcialmente OBSOLETO.** El literal `USING (true)` que denunciaba el
  diagnóstico (`013_mesa_qr.sql:22-24`, 3 policies) **ya fue remediado en el Paso 1**: hoy
  `sucursales`/`evolution_instances` están gateadas por `app.allow_qr_lookup` /
  `app.allow_instance_lookup` y existe la migración idempotente `018_fix_qr_public_rls.sql`.
  Grep de cierre `USING (true)` en `infra/` = **0**. **Residuo real que sí persiste**:
  `qr_token_public_lookup ON mesas USING (qr_token IS NOT NULL)` — y como `qr_token` es
  `NOT NULL` en todas las filas, el predicado es efectivamente *siempre verdadero* → cualquier
  SELECT sobre `mesas` puede leer filas de **otros tenants** (la policy es permissive y se
  combina con `tenant_isolation` por OR). No expone secretos, pero viola el invariante #1
  (aislamiento RLS). **Bloque E cierra este residuo**, no un `USING (true)` inexistente.
- **§3.E (config/merge):** vigente. `PATCH /admin/tenants/{id}` hace reemplazo total de `config`
  mientras `PATCH /tenants/me` hace merge → unificar a merge (H-9).

Hallazgos §3.B (AI_dialer) quedan OBSOLETOS por eliminación.

## 1. Contrato del `RubroManifest` (campos contractuales py↔ts)

`diccionario.py` (py) sigue siendo la **fuente de autoría**; `frontend/lib/rubros.ts` es el
**espejo**. La Fase A añade un **export canónico** y un **test de paridad** que falla ante
drift. Campos contractuales por rubro (los que el test compara byte a byte):

| campo | tipo | fuente py | espejo ts |
|---|---|---|---|
| `key` | str | `Rubro.key` | `RubroDef.key` |
| `nombre` | str | `Rubro.nombre` | `RubroDef.nombre` |
| `emoji` | str | `Rubro.emoji` | `RubroDef.emoji` |
| `sector` | str | `Rubro.sector` | `RubroDef.sector` |
| `labels` | obj (12 primitivas → label) | `Rubro.labels` | `RubroDef.labels` |
| `capacidades` | lista (orden CAP_ORDER) | `Rubro.capacidades` | `RubroDef.capacidades` |
| `sub_entidad_label` | str \| null | `Rubro.sub_entidad_label` | `RubroDef.subEntidadLabel` |
| `recurso` | bool (def. false) | `Rubro.recurso` | `RubroDef.recurso` |
| `variantes` | bool (def. true) | `Rubro.variantes` | `RubroDef.variantes` |
| `precio_medida` | bool (def. false) | `Rubro.precio_medida` | `RubroDef.precioMedida` |
| `categorias_semilla` | lista | `Rubro.categorias_semilla` | `RubroDef.categoriasSemilla` |

Top-level: `rubro_default`, `primitivas` (orden de las 12), `capacidades` (CAP_ORDER, las 22).
La **FSM/operativa** (estados de orden, roles de equipo) es **derivada pura** de `capacidades`
(`mesas`) + flag `recurso` (`operativa.py`/`operativa.ts`), por lo que comparar `capacidades` +
`recurso` la cubre; el test de paridad de operativa ya existente (`operativa.test.ts`) la valida
localmente. El manifiesto NO re-serializa la FSM (se mantiene derivada).

**Export canónico:** `backend/shared/rubros/export_manifest.py` (módulo puro) emite JSON
determinista (claves de rubro ordenadas alfabéticamente, `ensure_ascii=false`, `indent=2`,
`sort_keys` en labels via orden PRIMITIVAS). Regenerar el fixture:

```
python backend/shared/rubros/export_manifest.py > frontend/lib/__fixtures__/rubros.manifest.json
```

El **fixture** `frontend/lib/__fixtures__/rubros.manifest.json` es la verdad-py commiteada; el
test ts (`frontend/lib/rubros.parity.test.ts`) reconstruye el manifiesto desde las fuentes ts y
afirma igualdad profunda. Drift real (ts editado sin py, o viceversa tras regenerar) → falla.

## 2. Validación en publicación (fail-closed) — bloque B

- `TenantConfig` gana un **schema Pydantic** (`api_execute/app/schemas/tenant_config.py`):
  valida que `rubro`, si está presente, sea una clave conocida (`rubros_disponibles()`);
  rechaza rubro inválido en **publicación**:
  - onboarding (`auth_service`),
  - `PATCH /tenants/me` (`tenant_service`),
  - `PATCH /admin/tenants/{id}` (`admin_service`).
  Rubro inválido → **HTTP 422** (fail-closed). Decisión **H-6**: fail-closed en publicación.
- **Unificación merge (H-9):** `admin_service.update_tenant` pasa de **reemplazo total** de
  `config` a **merge** (mismo patrón que `tenant_service`) para no borrar `rubro`/`billing` por
  accidente.
- **Runtime:** `resolve_rubro`/`load_tenant_rubro` mantienen el fail-safe defensivo a
  `restaurante` (nunca se cae frente al cliente), pero ahora **loggeado** (no silencioso): un
  rubro inválido en runtime emite un `warning` con el tenant. Como la publicación es fail-closed,
  este camino solo se alcanza con datos legados/corruptos.

## 3. Fugas a cerrar y su gate — bloque C/D

| fuga | ubicación | gate | restaurante |
|---|---|---|---|
| `WELCOME_RULES_WHATSAPP` | `prompt_sections.py` → caller `ai_orchestrator` | `rubro` (default) exacto; otros: labels + `AGENDA`/`DELIVERY` | byte-idéntico |
| `WELCOME_RULES_MESA` | `prompt_sections.py` → `_build_mesa_prompt_section` | `rubro` (default) exacto; otros: neutral por labels | byte-idéntico |
| `_SUDAMERICA_CAPABILITIES/_RULES/_EXAMPLES` | `prompts_ai.py` | `rubro` (default) exacto; otros: variante neutral gateada por capacidad (MESAS/PEDIDOS/AGENDA) | byte-idéntico |
| `loyalty_outreach` | `loyalty_outreach.py` | `rubro` (default) exacto; otros: sin "en la carta", fallback "nuestro negocio" | byte-idéntico |
| `comanda_notify` sin `EN_PROCESO` | `comanda_notify.py` | añadir plantilla `("EN_PROCESO", None)` neutral | restaurante usa `EN_COCINA`, no `EN_PROCESO` → byte-idéntico |
| `TOOL_DEFINITIONS` sin filtro | `open_agent` `tools.py`/`agent_engine.py` | filtrar por capacidad del tenant (mapping tool→capacidad); tools core siempre on | restaurante tiene todas las caps gastro → 28 tools sin cambio |

**Principio de gate (patrón ya usado en `prompt_sections`):**
`if rubro_key == RUBRO_DEFAULT: return <CONSTANTE EXACTA>`; else neutralizar con labels /
capability-gates. Esto garantiza el guardrail byte-idéntico de restaurante mecánicamente.
Los labels de restaurante ("Carta" ≠ "menú") no reproducen ciertas curaciones históricas
("Ver el menú"), por lo que restaurante conserva su texto curado verbatim y sólo los demás
rubros pasan por el path label-driven.

**Mapping tool→capacidad (bloque D):** las tools de mesas (`crear_mesa`, `consultar_mesas`,
`modificar_mesa`, `eliminar_mesa`, `consultar_disponibilidad_mesas`) → `mesas`; comandas
(`consultar_comandas`, `cambiar_estado_comanda`) → `pedidos`; reservaciones
(`consultar/crear/modificar/cancelar_reservacion`) → `agenda`. El resto (ventas, catálogo,
clientes, métricas, equipo, modificadores) son **core**: siempre expuestas. Restaurante tiene
`mesas`+`pedidos`+`agenda` → conserva las 28 tools (byte-idéntico); una inmobiliaria (sin esas
caps) no ve `crear_mesa`.

## 4. Kernel sin fuga cross-tenant — bloque E

Migración nueva **idempotente** `infra/027_fix_public_rls.sql` (siguiente número tras `026`):
`DROP POLICY IF EXISTS qr_token_public_lookup ON mesas` + recrear gateada por
`current_setting('app.allow_qr_lookup', true) = 'true' AND qr_token IS NOT NULL`. El endpoint
público `/api/v1/public/mesas/qr/{token}` ya setea `app.allow_qr_lookup='true'` (via
`set_qr_lookup_context`) **antes** del SELECT filtrado por token exacto → el escaneo público
sigue vivo; fuera de ese contexto (peticiones normales de tenant) sólo aplica `tenant_isolation`.
No se edita la migración histórica `013`. Se incluye en la cadena local (glob `[0-9]*.sql`).

## 5. Decisiones D (defaults conservadores, §10 — no son STOP)

- **H-6 fail-open/closed:** fail-closed en publicación (422) + fail-safe **loggeado** en runtime.
- **H-9 merge/replace:** unificar a **merge**.
- **Alcance del manifiesto:** `diccionario.py` sigue siendo la fuente + validación + paridad +
  export JSON. **NO** se migra a tabla BD todavía (→ Paso 5).
- **Anclaje de versión:** NO se añade (se mantiene "fresco por mensaje").
- **i18n/multi-moneda:** NO entran al manifiesto (es-ES / CLP).
- **Rubro por-sucursal:** NO (se mantiene por-tenant).
- **Rename `mesas→recursos` / `comandas`:** NO (cosmético, diferido a Paso 5).

## 6. Verificación (bloque F)

- **Paridad py↔ts** verde y sensible a drift real.
- **Oráculo de prompt sin LLM (python puro):** los módulos de composición
  (`prompt_sections`, `prompts_ai`, `rubro_prompt`, `precio_medida`) son **puros** (solo
  `shared.rubros` + stdlib) e importables sin ORM/DB. Un test compone el prompt de restaurante y
  afirma **igualdad byte a byte** con un snapshot pre-cambio; para `peluqueria`/`ferreteria`/
  `veterinaria` afirma que las secciones restaurante-céntricas **ya no aparecen**.
- **Frontend** `typecheck` + `test` verdes (incl. paridad).
- **Entorno:** el host no trae `python`/`docker` en PATH, pero sí un Python portable
  (bundled del SDK / venv) que ejecuta los módulos **puros** y `pytest`. Lo que requiere
  pydantic se corre con el venv que lo trae; lo que requiere la app completa (FastAPI/DB/LLM)
  queda **verificado por lectura** y documentado.
