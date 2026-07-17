# Base de datos demo UNIFICADA — Aura Cosmética & Belleza (`aura-demo`)

> Objetivo: que cada subcategoría **visible** del sidebar canónico renderice con datos realistas y
> **coherentes entre pantallas** para el rubro `cosmetica_belleza`, simulando **un** negocio (no datos
> falsos por página). Seed reproducible en `tools/seed_demo_aura.mjs`.

## FASE 0 — Inventario (universo visible del rubro)

El rubro `cosmetica_belleza` declara **8 capacidades** (`rubros.ts` == tabla `rubros`):
`catalogo, pedidos, pagos, delivery, inventario, compras, fidelizacion, campanas`.

Al pasar cada sub por `subVisible()` (`frontend/lib/nav-canonico.ts`), el universo real es **49 subs en
11 categorías** — no ~90. Seis categorías completas quedan **ocultas** (0 subs visibles) porque el rubro
no tiene su capacidad:

| Oculta | Falta capacidad |
|---|---|
| Agenda | `agenda` |
| Contabilidad | `contabilidad` |
| Producción | `produccion` |
| Activos fijos | `activos_fijos` |
| Personas (RRHH) | `rrhh` |
| Proyectos | `proyectos` |

**Consecuencia de alcance:** la **OLA C** del prompt (doble partida, MRP/BOM, liquidaciones,
depreciación) **no aplica** a este demo: esas páginas no son alcanzables. La Definición de Hecho (§10)
—"cada sub *visible*"— se cumple sin construir esos dominios ERP.

Clasificación de las 49 subs visibles (grep de `StubModulo` sobre cada `page.tsx` canónico):

| Estado | N | Notas |
|---|---|---|
| **Real** (fetch propio) | 13 | dashboard, contactos/directorio, conversaciones/{bandeja,ia}, catalogo/productos, pedidos/ordenes, dinero/reportes, inventario/existencias, cuenta/{perfil,equipo,modulos,integraciones,facturacion} |
| **Stub** ("En construcción") | 35 | Compras (7), Inventario (5), Dinero (4), Contenido (4), Inicio (3), Contactos (2), Catálogo (3), Pedidos (2), Conversaciones (2), documentos/archivos, cuenta/{multiempresa,monedas} |
| **Falta página** (404) | 1 | `inicio/accesos-rapidos` (href en el nav, sin `page.tsx`) |

Estado de datos **antes** del seed: solo `productos`(26), `categorias`(4), `usuarios`(1). Todo lo demás
en 0 → incluso las 13 páginas reales mostraban vacío por **falta de seed**, no por ser stub.

## FASE 1 — Modelo de dominio (la "sola base de datos")

**Un pedido es el HECHO FUENTE.** Cada pedido se proyecta a varias lentes que deben cuadrar:

```
PEDIDO (fecha, cliente, vendedora, sucursal, canal, tipo_entrega, medio_pago, estado, 1–3 líneas)
   ├─► comanda + comanda_items   → dinero/reportes (financiero + operativo, COGS/margen)
   ├─► ventas (1 fila por línea)  → pedidos/ordenes, dashboard/revenue, top-productos
   └─► agregados del lead         → contactos/directorio (vista Clientes: total_gastado, tier)
```

Hallazgo clave del mapeo de contratos: **`leads` es la tabla de clientes/CRM** (no `contacts`, que no la
consume ninguna página). Los campos de fidelización viven en `leads`: `estado_cliente`
(`NUEVO/OCASIONAL/FRECUENTE/VIP/INACTIVO`), `total_gastado`, `total_pedidos`, `ultima_visita`,
`plato_favorito`, `frecuencia_dias`, `tags`. `ventas.lead_id → leads`.

Segundo hallazgo: **`dinero/reportes` (tabs Financiero/Operativo) lee `comandas`+`comanda_items`**, mientras
que revenue/top-productos leen `ventas`. Por eso el seed materializa **ambas** proyecciones del mismo
pedido y sus totales reconcilian.

**Empresa simulada:** 2 sucursales (Providencia principal + Viña del Mar), equipo de 4 (Camila ADMIN=demo
+ 3 asesoras), ventana de **12 meses** con estacionalidad (día de la madre, fiestas patrias, black
friday/navidad, san valentín) y leve crecimiento hacia el presente.

**Volúmenes (PyME de cosmética):** 150 leads (120 clientes con historial + 30 pipeline), ~550 ventas,
~360 comandas, ~590 líneas, 11 metas, 10 alertas, ~108 mensajes IA (18 hilos), 6 entradas de conocimiento.

**Máquinas de estado sembradas (mezcla realista):**
- Pedido/comanda: ~85% `ENTREGADO`, ~8% en curso (`PENDIENTE/EN_PROCESO/LISTO`, recientes), ~7% `CANCELADO`
  (los cancelados **no** generan `ventas`, para no inflar ingresos).
- Lead: clientes `estado='CONVERTIDO'`; pipeline `NUEVO/CONTACTADO/EN_PROCESO/DESCARTADO`.
- Cliente: tier por percentil de gasto + recencia (>120 días sin comprar ⇒ `INACTIVO`; top 15% ⇒ `VIP`).

## FASE 2 — Grafo de coherencia (qué hecho alimenta qué página)

| Hecho fuente | Tablas | Páginas encendidas |
|---|---|---|
| Pedido → líneas | `ventas` | pedidos/ordenes · dashboard (ventas_mes/revenue) · dinero/reportes (revenue, top) |
| Pedido → fulfillment | `comandas`,`comanda_items` | dinero/reportes (financiero, operativo: COGS, margen, ticket) |
| Cliente | `leads` (agregados) | contactos/directorio (CRM + Clientes) · dashboard (conversión, nuevos leads) |
| Equipo/sucursal | `usuarios`,`sucursales`,`sales_targets` | cuenta/equipo (leaderboard, metas) · cuenta/perfil · dashboard (meta_mes) |
| Conversación IA | `ai_conversations`,`tenant_knowledge`,`agente_config` | conversaciones/bandeja · conversaciones/ia · dashboard (ROI IA) |
| Catálogo/stock | `productos` (costo, stock_minimo) | catalogo/productos · inventario/existencias · márgenes |
| Alertas | `smart_alerts` | dashboard (alertas/next-best-action) |

**Invariante verificado:** para todo cliente, `leads.total_gastado == Σ ventas.total` (0 descuadres).

## FASE 3 — Plan por olas

- **OLA A — solo seed (13 páginas reales): ENTREGADA.** Ver más abajo.
- **OLA B — 35 stubs (tabla+endpoint+hook+desestub):** dominios simples CRUD/lectura — Compras,
  Inventario (movimientos/lotes/bodegas/valorización/transferencias), Dinero (ingresos/cobros/tesorería/
  flujo), Contenido, Contactos (segmentos/ficha), Catálogo (servicios/variantes/costos), Pedidos
  (entregas/devoluciones), Inicio (actividad/tareas/notificaciones), Conversaciones (canales/plantillas),
  documentos/archivos, cuenta/{multiempresa,monedas}. Migraciones `031+` con `IF NOT EXISTS`.
- **OLA C — eliminada** para este rubro (categorías ocultas).
- **1 página faltante:** construir `inicio/accesos-rapidos`.

### Reglas del seed (cumplidas)
Determinista (PRNG con semilla fija, sin `Math.random`), fechas relativas a hoy re-ancladas en cada
corrida, idempotente (borra datos demo del tenant y reinserta — probado: dos corridas ⇒ mismos conteos),
RLS-aware (fija `app.current_tenant_id`), un solo tenant. Script versionado en `tools/`, no en scratchpad.

## OLA A — Resultado (verificado EN VIVO vía API + auth `demo@aura.cl`)

Ejecución: `node tools/seed_demo_aura.mjs | psql "$DATABASE_URL"`

Conteos post-seed: `leads 150 · ventas 552 · comandas 363 · comanda_items 591 · sales_targets 11 ·
smart_alerts 10 · ai_conversations 108 · usuarios 4 · sucursales 2 · productos 26 (costo poblado)`.

Verificación por endpoint (logueado como demo):

| Página | Endpoint | Resultado |
|---|---|---|
| dashboard | `/metricas/dashboard` | ventas_mes $557.800 · meta $1.460.000 · conversión 78.7% · IA 6 atendidas · ROI IA |
| contactos/directorio | `/leads` (+ `estado_cliente=VIP`, `order_by=total_gastado`) | 150 leads; VIP top $899.500 |
| pedidos/ordenes | `/ventas` | 552 ventas paginadas |
| dinero/reportes | `/metricas/financiero` · `/operativo` · `/revenue` · `/productos-top` | revenue $539.800 · COGS $249.642 · margen 53.75% · serie 7 días · top 5 |
| inventario/existencias | `/productos` | 26 SKUs con stock/mínimo; 4 bajo mínimo |
| conversaciones/bandeja | `/ai/conversations` | 18 hilos |
| conversaciones/ia | `/ai/config` · `/ai/knowledge` | config auto + 6 conocimientos |
| catalogo/productos | `/productos` | 26 productos con foto |
| cuenta/equipo | `/usuarios` · `/sales-targets` | 4 usuarios · metas del mes |
| cuenta/perfil | `/tenants/me` · `/sucursales` | Aura (PRO) · 2 sucursales |
| cuenta/{modulos,integraciones,facturacion} | `/tenants/me` | render por config/plan (PRO) |

> Nota de verificación: se comprobó el **contrato de datos end-to-end** (login real → API real → datos
> coherentes) para cada página. La confirmación visual en navegador de las 13 páginas queda como paso
> manual (el frontend renderiza client-side con el token de sesión).
