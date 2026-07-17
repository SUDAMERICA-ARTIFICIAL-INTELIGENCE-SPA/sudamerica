# OLA B — Desestubar 35 páginas + 1 faltante (aura-demo, cosmetica_belleza)

> Continúa `demo-data-unificada.md` (OLA A, commit `f1cd0c1`). Misma filosofía: **coherencia > volumen**.
> La mayoría de OLA B son **lentes derivadas** de los hechos fuente de OLA A (ventas, comandas, leads,
> productos). Un solo dominio nuevo — **Compras/Proveedores** — introduce hechos fuente y **extiende el
> grafo de coherencia**: `compra → recepción (entrada stock) → factura (egreso caja / CxP)`.

## Recon confirmado (antes de tocar)

- Las **35** rutas objetivo son `StubModulo` (7 líneas c/u); `inicio/accesos-rapidos` **no tiene
  `page.tsx`** (404). Verificado por grep.
- Backend real disponible logueado como `demo@aura.cl` (el cortocircuito a fixtures `isDemoActive()`
  **solo aplica bajo `/showroom`** — `frontend/lib/demo/state.ts:34`). Todo lo sembrado se ve.
- El router `metricas` ya expone muchas lentes reutilizables: `/dashboard /operativo /revenue /por-canal
  /por-sector /productos-top /conversion /leads-estado /financiero /segmentacion-clientes
  /loyalty-insights /menu-engineering /weekly-activity`. Router `alertas` (`GET /alertas`), `leads`
  (`GET /leads`, `/leads/{id}`, `/leads/estado/{e}`), `ventas`, `sucursales`, `tenants/me` ya existen.
- Tablas OLA A relevantes (columnas clave): `comandas(metodo_pago, pago_confirmado, costo_delivery,
  tipo_entrega, estado, repartidor_nombre)`, `productos(costo, stock, stock_minimo, precio, imagen_url,
  unidad_venta)`, `repartidores`, `delivery_assignments`, `evolution_instances`. Existe `suministros`
  (insumo simple con `proveedor` varchar) y router `loyalty` (solo `POST /trigger-outreach`).
- Patrones frontend (de `existencias/page.tsx`, `dinero/reportes`): `PageHeader`+`SectionCard`+
  `EmptyState`; KPIs con `KpiCard`/`StatCard`; tablas `Table.*`+`Pagination`; charts **Recharts** +
  `lib/chart-config.ts`; hooks React Query espejo de `useProductos.ts` (`api.get<PaginatedResponse<T>>`,
  queryKey con `tenantId`, `enabled:!!tenantId`); moneda inline `Intl.NumberFormat("es-CL")`;
  `navItemsFlatCanonico(rubro)` para la grilla de accesos.

## Inventario de las 36 rutas (§2)

Leyenda: **D** = derivable de OLA A (0 tablas nuevas) · **D+B2** = derivable pero necesita el hecho
Compras · **N** = tabla nueva · **cfg** = config/solo-lectura.

### B1 — DERIVADAS (18, read-only) — EMPEZAR AQUÍ

| # | Ruta | Tipo | Fuente / endpoint | Acción |
|--|------|------|-------------------|--------|
| 1 | `contactos/segmentos` | D | `GET /metricas/segmentacion-clientes` (existe) | hook + página: conteos por `estado_cliente`/canal/tier + tabla |
| 2 | `contactos/ficha` | D | `/leads/{id}` + ventas(lead) + `/ai/conversations` + `/alertas` | endpoint `GET /leads/{id}/ficha` (agrega 360°) + timeline |
| 3 | `catalogo/costos` | D | `/productos` (costo, precio) | margen por SKU client-side (KPIs + tabla) |
| 4 | `catalogo/variantes` | D | `/productos` (unidad_venta, presentaciones) | agrupar presentaciones/precios read-only |
| 5 | `catalogo/servicios` | D | `/productos` categoría "Servicios" (seed) | sembrar ~8 servicios de belleza como productos; listar |
| 6 | `inventario/movimientos` | D+B2 | salidas=`ventas`, entradas=recepciones | endpoint kardex `GET /inventario/movimientos` |
| 7 | `inventario/valorizacion` | D | `/productos` (stock×costo) | valorización + bajo mínimo (KPIs+tabla) |
| 8 | `inventario/bodegas` | D | `/sucursales` como bodegas | stock por bodega (reparto determinista) |
| 9 | `dinero/ingresos` | D | `/metricas/revenue` + `/por-canal` | ingresos por periodo/canal (serie+breakdown) |
| 10 | `dinero/flujo-caja` | D+B2 | ingresos(ventas) − egresos(compras) | endpoint `GET /metricas/flujo-caja` |
| 11 | `dinero/cobros` | D | `comandas.metodo_pago/pago_confirmado` | endpoint `GET /metricas/cobros` (cobrado/pendiente) |
| 12 | `dinero/tesoreria` | D | saldos por medio de pago (comandas) | posición de tesorería por medio |
| 13 | `inicio/actividad` | D | feed ventas+leads+comandas+ai | endpoint `GET /metricas/actividad` (feed unificado) |
| 14 | `inicio/tareas` | D | `/alertas` + pendientes | tareas del día desde alertas |
| 15 | `inicio/notificaciones` | D | `/alertas` (existe) | lista de notificaciones |
| 16 | `contenido/vitrina` | D | `/productos` | catálogo público (grid con foto/precio) |
| 17 | `contenido/medios` | D | `productos.imagen_url` | biblioteca de medios |
| 18 | `contenido/fidelizacion` | D | `/metricas/loyalty-insights` + leads tiers | programa de puntos/tiers |

Backend nuevo B1 = **5 endpoints read-only** (`leads/{id}/ficha`, `inventario/movimientos`,
`metricas/{flujo-caja,cobros,actividad}`). **0 tablas nuevas** (salvo el seed de servicios como productos).

### B2 — Compras/Proveedores (7) — HECHO FUENTE NUEVO, núcleo

Migración `031_compras.sql` (RLS `tenant_isolation`, `IF NOT EXISTS`). Mini-dominio:
`proveedores`, `ordenes_compra`+`oc_items`, `recepciones`, `facturas_proveedor` (+ `requisiciones`,
`cotizaciones` ligeras). Router `compras` + hooks + desestub.

| # | Ruta | Tipo | Tabla/fuente | Acción |
|--|------|------|--------------|--------|
| 19 | `compras/proveedores` | N | `proveedores` | CRUD listado, KPIs (activos, CxP, lead time) |
| 20 | `compras/requisiciones` | N | `requisiciones` (o low-stock) | solicitudes internas de reposición |
| 21 | `compras/cotizaciones` | N | `cotizaciones` | RFQ por proveedor |
| 22 | `compras/ordenes` | N | `ordenes_compra`+`oc_items` | OC con estados + líneas |
| 23 | `compras/recepciones` | N | `recepciones` | recepción = **entrada** a inventario/movimientos |
| 24 | `compras/facturas` | N | `facturas_proveedor` | factura = **egreso** caja / CxP |
| 25 | `compras/evaluacion` | D | agregados de OC/recepción | scoring proveedor (puntualidad, cumplimiento) |

Seed: 20 proveedores de cosmética + 12 meses de OC coherentes con el consumo de las ventas de OLA A.
**Modelo económico realista:** el stock de apertura (valorizado ~$48M, heredado del catálogo) ya existía
antes de la ventana; dentro de los 12 meses la tienda solo **repone lo vendido + un buffer (~15%)**. Así
los egresos por compras (~$14M/12m con IVA) ≈ COGS y el flujo de caja mensual es coherente (ingresos
$19,5M > egresos). Invariante suave por SKU: `entradas_recibidas ≥ salidas` ⇒ kardex nunca negativo
(verificado: 0 filas en violación). Cierra el grafo: recepción→`inventario/movimientos`;
factura→`dinero/flujo-caja` (egreso) y CxP. OCs base = RECIBIDA con recepción+factura; ~8 OCs "en
tránsito" (BORRADOR/ENVIADA/CONFIRMADA/CANCELADA) aportan variedad de estados sin afectar el kardex.

### B3 — CRUD chicos / config (8)

| # | Ruta | Tipo | Tabla/fuente | Acción |
|--|------|------|--------------|--------|
| 26 | `pedidos/entregas` | D | `comandas` DELIVERY + `repartidores`/`delivery_assignments` | tablero de entregas |
| 27 | `pedidos/devoluciones` | N | `devoluciones` (mig 032) | RMA por venta |
| 28 | `conversaciones/canales` | D/cfg | `evolution_instances` | estado de canales (WA/IG/Web) |
| 29 | `conversaciones/plantillas` | N | `mensaje_plantillas` (mig 032) | plantillas de mensaje |
| 30 | `documentos/archivos` | N | `documentos_archivos` (mig 032) | biblioteca de documentos |
| 31 | `contenido/campanas` | N | `campanas` (mig 032, cap `campanas`) | campañas de marketing |
| 32 | `cuenta/multiempresa` | D/cfg | `/tenants/me` | vista multi-empresa (1 tenant) |
| 33 | `cuenta/monedas` | cfg | config (CLP) | monedas y formato |

Migración `032_olab_crud.sql`: `devoluciones`, `mensaje_plantillas`, `documentos_archivos`, `campanas`.

### B4 — Página faltante (1)

| # | Ruta | Tipo | Acción |
|--|------|------|--------|
| 34 | `inicio/accesos-rapidos` | — | crear `page.tsx`: grilla de accesos con `navItemsFlatCanonico(rubro)` |

## Resumen de alcance

- **Backend:** 2 migraciones (`031_compras.sql`, `032_olab_crud.sql`), routers `compras` + endpoints
  read-only (B1) + CRUD B3. **10 tablas nuevas** (6 compras + 4 B3). RLS en todas.
- **Frontend:** 35 desestubes + 1 página nueva, ~15–18 hooks nuevos, reusando patrones reales.
- **Seed:** `tools/seed_demo_aura_olab.mjs` (complementa OLA A; determinista, idempotente, RLS-aware).
- **Orden:** B1 (máx. reuso) → B2 (Compras, hecho nuevo) → B3 → B4. Gates verdes + verificación en vivo
  por sub-ola.

## OLA B — Resultado (verificado)

Ejecución seed: `node tools/seed_demo_aura_olab.mjs | psql "$DATABASE_URL"` (idempotente, tras OLA A).

**Conteos post-seed (aura-demo):** proveedores 20 · ordenes_compra 109 (51 RECIBIDA + 58 en tránsito/otras)
· oc_items 207 · recepciones 51 · recepcion_items 189 · facturas_proveedor 51 · requisiciones 12 ·
cotizaciones 15 · devoluciones 15 · plantillas 10 · documentos 24 · campañas 8 · servicios 8.

**Grafo de coherencia (verificado por SQL + API):**
- Compra→Recepción: 51 OC RECIBIDA ↔ 51 con recepción (1:1).
- Recepción→Factura: 51 recepciones ↔ 51 facturas (1:1).
- Egreso de caja Σ facturas = $14.452.886 = `compras/resumen.total_comprado_12m`.
- CxP (saldo pendiente) = $4.381.928 = `compras/resumen.cxp_total`.
- Kardex: entradas 840 u ≥ salidas 724 u (invariante por SKU: 0 violaciones).
- Flujo de caja mensual coherente: ingresos 12m $19,5M > egresos $14,4M.

**Gates verdes:**
- Frontend: `npm run typecheck` 0 errores · `npm run test` 807/807 · 34 rutas nuevas sirven HTTP 200 en dev.
- Backend: `pytest api_execute/tests` 588 passed. 3 fallos son **preexistentes/ambientales** (probado
  con `git stash`): `test_readiness` (microservicios peer caídos en local), `test_dashboard_ai_metrics`
  (flake de orden — pasa aislado), `test_create_sucursal_with_location_fields` (falla igual en árbol
  pristino). Cero regresiones de OLA B.
- 18 endpoints nuevos (compras×9, inventario/movimientos, metricas×4, devoluciones/plantillas/documentos/campanas)
  verificados con login real `demo@aura.cl` → HTTP 200 con datos.

**Endpoints/tablas nuevos:** migraciones `031_compras.sql` (8 tablas) + `032_olab_crud.sql` (4 tablas),
routers `compras`/`inventario`/`olab_crud` + endpoints read-only en `metricas`. Modelos JSON cross-dialect
(`sqlalchemy.JSON`, no `JSONB`) para compatibilidad con el harness de test en SQLite.

> Nota: se verificó el contrato de datos end-to-end (login real → API real → datos coherentes) para las
> 34 páginas y la confirmación de compilación/servicio (HTTP 200) de cada ruta. La confirmación visual
> pixel-a-pixel en navegador queda como paso manual (render client-side con token de sesión), igual que OLA A.

---

## QA Vitrina (showroom) — 2026-07-12

QA de la **vitrina navegable** (`/showroom/<rubro>/<ruta>`, modo demo sin backend). Método: barrido
headless con render real de cada página en jsdom (React Testing Library), fijando el rubro por la URL y
capturando por página: warnings del resolver (`[demo] sin snapshot…` = hueco de fixture), crashes
(ErrorBoundary), EmptyState y branding del tenant. Cobertura: **héroe `cosmetica_belleza` en las 105 rutas
reales + muestra de 6 rubros** (restaurante, inmobiliaria, taller_mecanico, gimnasio, hotel, ferreteria) en
12 rutas clave.

**Hallazgo corregido — rutas legacy de puro `redirect()` contaminaban el registro del showroom.**
El generador `tools/gen_showroom_routes.mjs` escaneaba TODA página bajo `(dashboard)`, incluyendo **49
stubs planos** cuyo único cuerpo es `redirect("/ruta/canonica")` (compat de deep-links viejos, Paso 7). En
la vitrina esos `redirect()` saltan a una ruta **absoluta sin el prefijo `/showroom/<rubro>`** → navegan
FUERA del showroom (romperían la navegación / caerían en la app real con auth). Fix: el generador ahora
**excluye las páginas puro-redirect** (heurística: llaman `redirect(` y no renderizan JSX). El registro pasó
de **154 → 105 rutas**; los destinos canónicos (p.ej. `/pedidos/ordenes`, `/dinero/reportes`) ya estaban
mapeados, así que no se pierde ninguna vista.

**Verificado sano:**
- **0 crashes** y **0 endpoints sin snapshot** en todo el barrido (tras el fix). La cobertura de fixtures
  del resolver (snapshot héroe + reskin + sintético/vacío) es total para lo que las páginas piden.
- **Branding por rubro correcto** (determinista): el tenant resuelto trae `config.rubro` propio
  (héroe `cosmetica_belleza` → "Aura Cosmética & Belleza"; resto vía `buildTenant(rubro)`). El sidebar sigue
  al rubro de la URL una vez cargado el tenant.
- **EmptyStates residuales = coherentes, no defectos.** `agenda/reservas` y `pedidos/mesas` muestran vacío
  porque los snapshots `/reservaciones` y `/mesas` son **0 filas en el seed real** (la cuenta cosmética no
  usa reservas ni mesas) → fiel al dashboard logueado. `conversaciones/bandeja` muestra "Selecciona una
  conversación" (panel de detalle de un master-detail antes de elegir hilo; la lista sí está poblada).
- **51 subs muestran `StubModulo` ("En construcción")** para el héroe: es el comportamiento REAL del
  dashboard (subs canónicas sin página propia todavía), coherente entre vitrina y app logueada.

**Pendiente de confirmación visual en navegador:** overflow horizontal y fidelidad pixel-a-pixel no se
verificaron con browser real — el chromium headless aborta el renderer con el bundle **de dev** en este
entorno WSL2 (crash en libc, no defecto del producto). Se hará contra el **export estático de Fase 3**
(bundle de producción, mucho más liviano). Riesgo de overflow acotado analíticamente: el reskin escala
montos con clamp ≤400×, manteniéndolos en rangos que el layout real ya maneja (CLP en millones es normal
para rubros de alto ticket como inmobiliaria).

**Gates:** `npm run typecheck` 0 errores · `npm run test` **809/809** · registro regenerado a 105 rutas.

## Fase 3 — Export estático de la vitrina (GitHub Pages) — 2026-07-13

La vitrina pública es un **export estático del frontend en modo showroom**, gateado por env para NO tocar
el build real. `STATIC_EXPORT=1 npm run build` ⇒ `output:"export"`, `basePath:"/sudamerica"`,
`assetPrefix`, `images.unoptimized`, `trailingSlash`. Sin la env, el default sigue siendo
`output:"standalone"` (deploy real con backend). Ambos builds quedan verdes.

**Qué se materializa (`generateStaticParams` del catch-all `showroom/[rubro]/[[...ruta]]`):**
- **101 landings** (una por rubro) → `/showroom/<rubro>/` = dashboard/resumen.
- **105 subs del héroe** `cosmetica_belleza` → deep-link directo servible como archivo.
- Total **206 params** + el panel `/showroom` = 207 páginas de showroom en `out/`.
- Las claves de ruta se emiten aparte en `lib/demo/showroom-routes.keys.ts` (server-safe, SIN `"use client"`):
  el registro `.generated.tsx` es módulo cliente y sus claves no son legibles desde un server component.
- La página se dividió en **server** (`page.tsx`, con `generateStaticParams`) + **cliente** (`client.tsx`),
  porque un `"use client"` no puede exportar `generateStaticParams`.

**Fallback SPA (`app/not-found.tsx` → `404.html`):** las subs de rubros NO-héroe no se pre-renderizan a
archivo; en hard-load/refresh Pages sirve `404.html`, que lee `window.location`, reactiva el demo + monta
el shell del showroom en cliente. Así "todos los rubros navegables" aguanta también deep-links directos
(no solo navegación client-side). Verificado con server local: landings/subs-héroe → 200, deep-link
no-héroe (`restaurante/pipeline`) → 404-fallback, assets `/sudamerica/_next/…` → 200.

**Arreglos de export:**
- `isDemoActive()` ahora **descuenta el basePath** antes de comparar con `/showroom` (bajo Pages el
  pathname real es `/sudamerica/showroom/…`; sin esto el demo quedaba inactivo y la vitrina pegaría al
  backend inexistente). En el build real basePath="" → sin efecto.
- `useSearchParams()` sin Suspense en `cuenta/facturacion` → envuelto en `<Suspense>` (bailout a CSR
  rompía el prerender). `reset-password` ya lo tenía.
- `contenido/medios`: `fallbackSrc` de `placehold.co` → **SVG data-URI local** (sin host externo).
- Favicon (`<link>` de HTML crudo, que Next no reescribe con basePath) → prefijado con `NEXT_PUBLIC_BASE_PATH`.
- `.nojekyll` en `public/` (Pages ignora `_next/` sin él).

**Seguridad del bundle público:** scan de secretos en `out/` limpio; los únicos env inyectados son
`NEXT_PUBLIC_*` (por diseño públicos) y apuntan solo a localhost — nada interno horneado. Las URLs
`https://demo.aura.cl/docs/*.pdf` de los snapshots son hrefs de datos del seed (no imágenes ni secretos).

**Confirmación visual en navegador — bloqueada por el entorno (no por el producto):** se reintentó el
screenshot headless contra el bundle **de producción** (más liviano) y el chromium **igual aborta el
renderer** en este WSL2 (mismo crash de libc, sin capturar ni una página). Queda para la **URL desplegada**
(Fase 4), abrible en un navegador real. La correctitud de routing/branding/coherencia sí está verificada
(HTTP smoke + barrido jsdom); el pendiente es solo overflow pixel-a-pixel, de riesgo acotado.

**Gates Fase 3:** `STATIC_EXPORT=1 npm run build` verde (207 páginas showroom, `out/` 48 MB) ·
`npm run build` standalone verde (genera `.next/standalone`) · `typecheck` 0 · `test` **809/809**.

## Fase 4 — Deploy a GitHub Pages (CI) — 2026-07-13

**Objetivo:** publicar la vitrina (export estático de Fase 3) en GitHub Pages, con
build automatizado en CI y sin intervención manual de archivos.

**Workflow:** `.github/workflows/pages.yml`
- **Trigger:** `push` a `paso7-dashboard-canonico` + `workflow_dispatch` (manual).
- **Job `build`** (`working-directory: frontend`): `actions/checkout@v4` →
  `actions/setup-node@v4` (Node 20, cache npm sobre `frontend/package-lock.json`) →
  `npm ci` → `STATIC_EXPORT=1 npm run build` → `actions/configure-pages@v5` →
  `actions/upload-pages-artifact@v3` con `path: frontend/out`.
- **Job `deploy`** (`needs: build`): `actions/deploy-pages@v4` sobre el environment
  `github-pages`.
- **Permisos:** `contents: read`, `pages: write`, `id-token: write`.
- **Concurrency:** grupo `pages`, sin cancelar el deploy en curso.

**Pages source:** GitHub Actions (habilitado vía API `build_type: workflow`).

**URL:** https://sudamerica-artificial-inteligence-spa.github.io/sudamerica/
(redirige a `/sudamerica/showroom/` → landing del héroe `cosmetica_belleza`).

**Nota sobre el build real:** el workflow activa el modo export **solo** con
`STATIC_EXPORT=1`; `npm run build` sin esa env sigue produciendo `output: "standalone"`.
CI no despliega el backend ni degrada el build de producción.
