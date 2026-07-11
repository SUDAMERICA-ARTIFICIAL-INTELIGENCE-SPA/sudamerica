# Bitacora del Modulo Carta & Menu

> **Ultima actualizacion**: 2026-04-12
> **Estado**: OPERATIVO (CRUD + Import con preview/confirm + imagenes por plato + envio PDF WhatsApp)
> **Servicio principal**: `api_execute` (:8000)
> **Frontend**: `/carta` en frontend

---

## 1. Proposito del modulo

Carta & Menu centraliza toda la gestion del menu gastronomico de un tenant:
- Crear/editar categorias, platos, modificadores, suministros y recetas.
- Importar menus masivamente desde PDF, CSV, imagen o URL con revision manual antes de persistir.
- Versionar cada importacion para auditoria y rollback.
- Asociar imagenes a cada plato (conversion automatica a WebP + thumbnails).
- Exponer el menu al cliente por WhatsApp (PDF oficial enviado por el agente IA).
- Alimentar el KDS (Kitchen Display System) con comandas derivadas de los platos.

Cumple el flowchart oficial `Docs/flujos/Carga_menu.pdf`.

---

## 2. Microservicios involucrados

| Servicio | Puerto | Rol en Carta & Menu |
|---|---|---|
| **api_execute** | :8000 | Dueno unico del CRUD de productos, categorias, modifiers, comandas, mesas, suministros, recetas, menu imports. Expone WebSocket KDS. Orquesta las llamadas de la IA. |
| **AI_dialer** | :8001 | Parsea pedidos en lenguaje natural y pide creacion de comandas a api_execute. Guarda `menu_pdf_url` y `menu_cabecera_url` en `agente_config`. Expone `PATCH /api/v1/ai/config` para que api_execute actualice el PDF oficial tras un import. |
| **canales_service** | :8004 | Recibe mensajes WhatsApp via Evolution API, los enruta a api_execute, y cuando la respuesta del agente incluye un adjunto lo envia al cliente (`sendMedia` a Evolution API). Tambien maneja el scan del QR de mesa. |
| **Evolution API** | VM :8080 | Infraestructura WhatsApp. Corre en Compute Engine VM (Meta bloquea IPs de Cloud Run). Envia documentos, imagenes, audio y poll. |

### Comunicacion inter-servicios

```
Admin (Web)
  │  JWT Bearer
  ▼
api_execute ── CRUD directo ──> PostgreSQL (Cloud SQL + RLS por tenant)
  │                                   ▲
  │                                   │
  │  PATCH /api/v1/ai/config           │  reads agente_config
  ▼  (internal JWT + tenant header)    │
AI_dialer ─────────────────────────────┘

Cliente WhatsApp
  │
  ▼
Evolution API (VM) ──> canales_service ──> api_execute.orchestrate_chat()
                                                 │
                                                 │ delega razonamiento
                                                 ▼
                                            AI_dialer (LLM)
                                                 │
                                    respuesta + attachments
                                                 ▼
                               canales_service.send_media_via_evolution()
                                                 │
                                                 ▼
                                      Evolution API → cliente
```

**Auth inter-servicios**: JWT interno con `INTERNAL_SERVICE_SECRET_KEY` distinto por servicio. `build_service_auth_headers()` en `shared/middleware/auth.py` emite el token, `require_user_or_service` lo valida.

---

## 3. Servicios GCP utilizados

| Servicio GCP | Uso en Carta & Menu |
|---|---|
| **Cloud Run** | Hosting de api_execute, ai_dialer, canales_service, frontend. Cada uno con SA `456595931835-compute@developer.gserviceaccount.com`. |
| **Cloud SQL** | PostgreSQL 16 `sudamerica-db` (34.133.88.146), DB `sudamerica`. Multi-tenant via Row-Level Security sobre `tenant_id`. |
| **Cloud Storage** | Bucket `sudamerica-media` para PDFs originales y generados, y `sudamerica-menu-images` para imagenes de plato. |
| **Artifact Registry** | Imagenes Docker: `us-central1-docker.pkg.dev/sudamerica-prod/sudamerica/<service>:latest`. |
| **Cloud Build** | CI/CD: `backend/cloudbuild.yaml` y `frontend/cloudbuild-frontend.yaml`. |
| **Secret Manager** | `INTERNAL_SERVICE_SECRET_KEY` por servicio, `LLM_PROVIDER_KEY_MASTER_KEY`, `WEBHOOK_TOKEN`. |
| **Compute Engine** | VM `evolution-api-vm` en `us-central1-f` (IP 34.61.234.182:8080) — requerida porque Meta bloquea IPs de Cloud Run. |

---

## 4. Modelo de datos

### Tablas del modulo

| Tabla | Proposito | Owner |
|---|---|---|
| `categorias` | Secciones del menu (Entradas, Platos Fuertes, Bebidas...) | api_execute |
| `productos` | Items del menu con precio, costo, stock, imagen_url, disponible | api_execute |
| `modifier_groups` | Grupos de opciones (Tamano, Toppings) — `SINGLE_SELECT` \| `MULTI_SELECT` | api_execute |
| `modifiers` | Opciones individuales con `precio_delta` | api_execute |
| `producto_modifier_groups` | M:N entre productos y grupos de modifiers | api_execute |
| `suministros` | Ingredientes/insumos con stock, costo, proveedor | api_execute |
| `recetas` | M:N entre producto y suministros con `cantidad_necesaria` | api_execute |
| `mesas` | Mesas fisicas con `qr_token` para scan-to-order | api_execute |
| `sucursales` | Sedes (multi-sucursal Fase 1 deployada) | shared |
| `comandas` | Pedidos con FSM `PENDIENTE → EN_COCINA → LISTO → ENTREGADO` | api_execute |
| `comanda_items` | Lineas de pedido con `modifiers_json` (JSONB) | api_execute |
| `menu_imports` | **NUEVO** — Historial de imports con metadatos + preview + versionado | api_execute |
| `agente_config` | `menu_pdf_url` + `menu_cabecera_url` consumidos por el AI | ai_dialer |

### Diagrama de relaciones principales

```
categorias ──1:N──> productos ──M:N──> modifier_groups ──1:N──> modifiers
                        │
                   recetas (M:N)──> suministros
                        │
               comanda_items ──N:1──> comandas
                                        │
                              sucursales ──1:N──> mesas (con qr_token)

menu_imports  (N por tenant, ordenado por version DESC)
agente_config (1 por tenant)
```

### Tabla `menu_imports` (DDL)

Definida en `backend/infra/017_menu_imports.sql`. Cada fila representa **una importacion** (=una version del menu), tanto PDF/CSV/IMG como URL. Flujo: `status=PENDING` tras el preview → `CONFIRMED` tras confirmar → productos/categorias creados.

| Columna | Tipo | Proposito |
|---|---|---|
| `id` | UUID PK | Id de la importacion |
| `tenant_id` | UUID FK | Owner del import |
| `version` | INT | Numero incremental por tenant (`MAX(version)+1`) |
| `source_type` | VARCHAR(20) | `PDF` \| `CSV` \| `IMAGE` \| `URL` |
| `filename` | VARCHAR(500) | Nombre original del archivo |
| `original_pdf_path` | TEXT | Blob path permanente en GCS |
| `original_pdf_url` | TEXT | Signed URL (7d) del PDF original |
| `file_size_bytes` | INT | Tamano del archivo subido |
| `content_type` | VARCHAR(100) | MIME del archivo |
| `items_extracted` | INT | Cantidad de items detectados por la IA |
| `items_confirmed` | INT | Cantidad confirmada por el admin |
| `categories_created` | INT | Categorias nuevas creadas tras confirmar |
| `preview_data` | JSONB | `{items: [...]}` mientras `status=PENDING` |
| `status` | VARCHAR(20) | `PENDING` \| `CONFIRMED` \| `CANCELLED` |
| `set_as_official` | BOOLEAN | Si el PDF fue marcado como menu oficial del tenant |
| `activo` | BOOLEAN | Soft-delete |
| `created_at` / `updated_at` | TIMESTAMPTZ | Auditoria |

**RLS policy**: `tenant_isolation` filtra por `current_setting('app.current_tenant_id', true)`.

Indices:
- `idx_menu_imports_tenant` en `(tenant_id)`
- `idx_menu_imports_tenant_version` en `(tenant_id, version DESC)`

### FSM de Comandas

```
PENDIENTE ──> EN_COCINA ──> LISTO ──> ENTREGADO
      │             │             │
      └─────────────┴─────────────┴──────> CANCELADO
```

Definido en `frontend/lib/enums.ts` (`COMANDA_TRANSITIONS`). Backend valida transiciones en `services/comanda_svc.py` y devuelve 422 si son invalidas.

---

## 5. Endpoints del modulo

Todos viven en **api_execute** bajo `/api/v1/core/`.

### Productos

| Metodo | Ruta | Auth | Proposito |
|---|---|---|---|
| `GET` | `/productos` | CartaReader | Listar con filtros |
| `POST` | `/productos` | CartaWriter | Crear |
| `GET` | `/productos/{id}` | CartaReader | Detalle |
| `PATCH` | `/productos/{id}` | CartaWriter | Update parcial |
| `DELETE` | `/productos/{id}` | AdminWriter | Soft-delete |
| `PATCH` | `/productos/{id}/activar` | AdminWriter | Restaurar |
| `POST` | `/productos/{id}/imagen` | AdminWriter | Subir imagen |
| `DELETE` | `/productos/{id}/imagen` | AdminWriter | Eliminar imagen |

### Categorias, Modifiers, Suministros

CRUD estandar en `/categorias`, `/modifier-groups`, `/modifier-groups/productos/{producto_id}` (asignar grupos a plato), `/modifiers`, `/suministros`, `/recetas`.

### Menu Import (preview/confirm workflow)

| Metodo | Ruta | Auth | Proposito |
|---|---|---|---|
| `POST` | `/menu/import` | AdminWriter | Legacy: extrae y crea en un paso (backward compat) |
| `POST` | `/menu/import-url` | AdminWriter | Scraping via Browserless.io |
| `POST` | `/menu/import/preview` | AdminWriter | **Fase 1**: sube PDF a GCS, extrae items con IA, crea fila `menu_imports` con `status=PENDING`, retorna items para review |
| `POST` | `/menu/import/confirm` | AdminWriter | **Fase 2**: admin confirmo los items, crea productos/categorias, marca `CONFIRMED`. Si `set_as_official_pdf=true`, llama a AI_dialer para setear `agente_config.menu_pdf_url` |
| `GET` | `/menu/import/history` | AdminWriter | Lista paginada de importaciones pasadas |

### Comandas / KDS

- `GET /comandas` — filtros por `estado`, `tipo_entrega`, `canal_origen`
- `GET /comandas/kds` — vista Kanban agrupada por estado
- `POST /comandas` — crear (broadcast WebSocket)
- `PATCH /comandas/{id}/estado` — transicion FSM
- `DELETE /comandas/{id}` — cancelar
- `WS /ws/kds` — WebSocket tenant-scoped con eventos `comanda_created`, `comanda_updated`, `comanda_deleted`

### Mesas y QR

- CRUD en `/mesas`
- `GET /public/mesa_qr` — endpoint publico (sin JWT) para el scan del QR

### Metricas del menu

- `GET /metricas/menu/top` — top productos por unidades/ingresos
- `GET /metricas/menu/engineering` — clasificacion STAR/PUZZLE/PLOWHORSE/DOG
- `GET /metricas/menu/financiero` — food cost %, margen, ticket promedio

---

## 6. Flujos end-to-end

### Flujo A — Importacion con preview

```
1. Admin abre /carta → click "Importar Menu"
2. Drop file (PDF/CSV/PNG/JPG/WebP) o pega URL
3. Frontend: useMenuImportPreview().mutate(file)
     → POST /menu/import/preview
4. Backend menu_import_svc.extract_preview():
     a. upload_bytes() → GCS `tenants/{tid}/media/menu-original/{uuid}.pdf`
     b. generate_signed_url() → URL temporal
     c. Gemini Vision extrae items via _build_ai_extraction_payload() + _call_ai_extraction()
     d. _next_version(db, tenant_id) → MAX(version)+1
     e. db.add(MenuImport(status=PENDING, preview_data={items}))
     f. return {import_id, items, source_type, filename}
5. Frontend transicion a estado REVIEW:
     - Tabla editable (Mantine Table + TextInput/NumberInput/Autocomplete)
     - Admin corrige nombres, descripciones, precios, categorias
     - Checkbox "Usar este PDF como menu oficial para WhatsApp" (solo PDF)
6. Click "Confirmar importacion":
     → POST /menu/import/confirm
7. Backend menu_import_svc.confirm_import():
     a. Valida que record exista y este en PENDING
     b. _bulk_create(items, tenant_id, db) — crea categorias faltantes + productos
     c. record.status = CONFIRMED, items_confirmed, categories_created
     d. Si set_as_official: _update_official_menu_pdf() → PATCH http a AI_dialer
8. Frontend estado RESULT con botones:
     - "Agregar imagenes a platos" → abre ImageUploadDrawer
     - "Cerrar"
```

### Flujo B — Carga de imagen por plato

```
1. Admin en /carta → edita un plato (modal ProductoForm)
2. Al tope del modal ve "Imagen del plato":
     - Sin imagen: boton "Subir imagen (PNG, JPG, WebP)"
     - Con imagen: preview 80x80 + "Cambiar" / "Eliminar"
3. FileButton de Mantine core abre selector de archivo
4. useUploadProductImage().mutate({productoId, file})
     → POST /productos/{id}/imagen (multipart)
5. Backend image_storage_svc.upload_product_image():
     a. Valida MIME y tamano (max 5 MB, PNG/JPEG/WebP)
     b. Pillow.convert(RGB) + thumbnail(1600x1600) → WebP q=82
     c. Thumbnail adicional 400x400 → WebP q=75
     d. upload_bytes a bucket sudamerica-menu-images
     e. Actualiza producto.imagen_url
6. Frontend invalida query productos → card muestra nueva imagen
```

**Flujo B2 (carga secuencial post-import)**: tras confirmar un import, el admin puede abrir el `ImageUploadDrawer` que muestra cada plato sin `imagen_url` con un mini FileButton y un contador "3 de 12 con imagen".

### Flujo C — Cliente pide el menu por WhatsApp

```
1. Cliente: "envíame la carta"
2. Evolution API webhook → canales_service → api_execute.orchestrate_chat()
3. _load_agent_config() carga agente_config:
     - menu_pdf_url  (preferente si fue marcado como oficial)
     - menu_cabecera_url (imagen preview opcional)
4. _build_media_rules_section() inyecta MEDIA_RULES_MENU en el system prompt
5. AI_dialer (Gemini/GPT) responde "¡Claro! Te envío la carta ahora"
6. _auto_attach_menu_pdf() detecta intencion via _MENU_REQUEST_RE:
     - Si menu_pdf_url existe → la usa
     - Si no existe → _auto_generate_menu_pdf() via menu_pdf_service.py
       (carga productos → agrupa variantes → genera PDF con FPDF → sube a GCS)
7. orchestrate_chat() retorna response con:
     media_url, media_type="document", media_file_name="Menu.pdf"
8. canales_service.send_media_via_evolution():
     POST /message/sendMedia/{instance} a Evolution API
     payload: {number, mediatype: "document", media: <signed_url>, fileName: "Menu.pdf"}
9. Cliente recibe el PDF en su WhatsApp
```

### Flujo D — Pedido por WhatsApp llega al KDS

```
1. Cliente: "1 hamburguesa clasica con queso extra y 1 coca"
2. canales_service → api_execute → AI_dialer parsea intent=ORDER
3. ai_orchestrator._try_create_comanda():
     - GET /productos (fuzzy match "hamburguesa clasica")
     - GET /modifier-groups/productos/{id} (match "queso extra")
     - POST /comandas {tipo_entrega: MESA|DELIVERY|RETIRO, items: [...]}
4. Backend comanda_svc.create():
     - Inserta comanda + comanda_items
     - Broadcast via /ws/kds: {type: "comanda_created", data: {...}}
5. KDSBoard en frontend recibe evento → aparece card en columna PENDIENTE
6. Staff marca EN_COCINA → LISTO (PATCH /comandas/{id}/estado)
7. Cuando pasa a LISTO:
     - comanda_notify.notify_order_ready() → mensaje WhatsApp al cliente
8. Staff marca ENTREGADO
```

---

## 7. Permisos (RBAC)

Definidos en `backend/api_execute/app/routes/deps.py`. Claims del JWT: `role`, `sucursal_id`, `tenant_id`.

| Dependency | Roles permitidos |
|---|---|
| `CartaReader` | SUPERADMIN, ADMIN, ASESOR, VIEWER |
| `CartaWriter` | SUPERADMIN, ADMIN |
| `ComandaReader` | SUPERADMIN, ADMIN, PERSONAL, MESERO, COCINA, CAJA |
| `ComandaWriter` | SUPERADMIN, ADMIN, PERSONAL, MESERO, COCINA, CAJA |
| `AdminWriter` | SUPERADMIN, ADMIN |
| `ModifierReader` / `ModifierWriter` | Jerarquia igual a Carta |
| `AnyAuthenticated` | Cualquier usuario con JWT valido |

---

## 8. Archivos clave

### Backend

| Archivo | Proposito |
|---|---|
| `backend/infra/017_menu_imports.sql` | DDL `menu_imports` + indices + RLS |
| `backend/api_execute/app/models/menu_import.py` | Modelo SQLAlchemy `MenuImport(TenantBase)` |
| `backend/api_execute/app/models/{producto,categoria,modifier,comanda,suministro,mesa}.py` | Resto de modelos |
| `backend/api_execute/app/schemas/menu_import.py` | `MenuImportPreviewItem`, `PreviewResponse`, `ConfirmRequest`, `ConfirmResponse`, `HistoryItem` |
| `backend/api_execute/app/services/menu_import_svc.py` | `extract_preview()`, `extract_preview_csv()`, `confirm_import()`, `_update_official_menu_pdf()`, `get_import_history()`, `_bulk_create()` |
| `backend/api_execute/app/services/menu_pdf_service.py` | `generate_menu_pdf()` — FPDF + size grouping + upload GCS |
| `backend/api_execute/app/services/image_storage_svc.py` | `upload_product_image()`, `delete_product_image()`, `batch_download_and_upload()` |
| `backend/api_execute/app/services/ai_orchestrator.py` | `_MENU_REQUEST_RE`, `MEDIA_RULES_MENU`, `_auto_attach_menu_pdf()`, `_auto_generate_menu_pdf()` |
| `backend/api_execute/app/routes/menu_import.py` | Endpoints `/menu/import`, `/preview`, `/confirm`, `/history`, `/import-url` |
| `backend/api_execute/app/routes/productos.py` | CRUD + upload/delete imagen |
| `backend/api_execute/app/routes/comandas.py` | CRUD + KDS + FSM |
| `backend/api_execute/app/routes/ws_kds.py` | WebSocket real-time del KDS |
| `backend/shared/utils/storage.py` | `upload_bytes`, `generate_signed_url`, `build_media_path`, `public_url` |
| `backend/shared/middleware/auth.py` | `build_service_auth_headers`, `require_user_or_service` |

### Frontend

| Archivo | Proposito |
|---|---|
| `frontend/app/(dashboard)/carta/page.tsx` | Pagina con Tabs Platos/Modificadores. Contiene `ProductoForm` inline con upload de imagen via `FileButton` |
| `frontend/components/carta/MenuImportModal.tsx` | Modal con 3 estados: upload → review (tabla editable) → result |
| `frontend/components/carta/ImageUploadDrawer.tsx` | Drawer para subir imagenes a platos sin imagen post-import |
| `frontend/components/carta/ModifierEditor.tsx` | CRUD de modifier_groups + modifiers |
| `frontend/components/comandas/KDSBoard.tsx` | Kanban KDS con WebSocket |
| `frontend/hooks/useProductos.ts` | CRUD productos |
| `frontend/hooks/useCategorias.ts` | CRUD categorias |
| `frontend/hooks/useModifiers.ts` | CRUD modifier groups |
| `frontend/hooks/useMenuImport.ts` | Import legacy directo (backward compat) |
| `frontend/hooks/useMenuImportUrl.ts` | Import desde URL |
| `frontend/hooks/useMenuImportPreview.ts` | Hooks `useMenuImportPreview()` + `useMenuImportConfirm()` |
| `frontend/hooks/useUploadProductImage.ts` | Upload/delete imagen de plato |
| `frontend/hooks/useKDSWebSocket.ts` | Conexion WebSocket al KDS |
| `frontend/lib/types.ts` | Interfaces `Producto`, `Categoria`, `ModifierGroup`, `Modifier`, `Comanda`, `Mesa`, `MenuImportPreview*`, `MenuImportConfirmResult`, `MenuImportHistoryItem` |
| `frontend/lib/enums.ts` | `COMANDA_TRANSITIONS`, `ModifierGroupTipo`, `TipoEntrega` |

---

## 9. Historial de cambios

### 2026-04-12 — Flujo Carga_menu.pdf completado

Cerrados los 7 gaps identificados vs `Docs/flujos/Carga_menu.pdf`:

1. **PDF original en GCS** — `extract_preview()` sube el archivo a `tenants/{tid}/media/menu-original/{uuid}.<ext>` antes de extraer.
2. **Metadatos en BD** — Nueva tabla `menu_imports` con todo el tracking.
3. **Pantalla de revision** — `MenuImportModal` ahora tiene flujo upload→review→result con tabla editable.
4. **Versionado** — Campo `version` auto-incremental por tenant. `GET /menu/import/history` lista pasadas.
5. **UI de imagen por plato** — `ProductoForm` en `/carta` ahora tiene seccion "Imagen del plato" al tope del modal de edicion (FileButton de Mantine core).
6. **Loop de carga secuencial** — `ImageUploadDrawer` post-import muestra todos los platos sin imagen con mini-dropzone cada uno.
7. **PDF oficial = original subido** — Checkbox en review transmite `set_as_official_pdf:true`; `confirm_import()` hace PATCH interno a AI_dialer para actualizar `agente_config.menu_pdf_url`. El orchestrator lo consume tal cual.

### Historico previo

- **2026-03-17**: Multi-Sucursal Fase 1 — `sucursales`, routing por sucursal en WhatsApp.
- **2026-03-15**: WhatsApp media + STT — buckets `sudamerica-media` + Whisper STT.
- **2026-03-14**: Import CSV/PDF inicial (sin review, sin versionado) — legacy `POST /menu/import`.
- **2026-03-13**: Sudamérica AI Resto Fase 1 — modifiers, comandas, KDS, sidebar 4-pillar.
- **2026-03-10**: Cloud SQL RLS fixes — policy `auth_lookup`, `session.py` parseo de `?host=/cloudsql/...`.

---

## 10. Comandos operativos

### Deploy backend (api_execute)

```bash
cd D:/Sudamérica.AI/MVP/MVP/backend
gcloud builds submit --config cloudbuild.yaml --project sudamerica-prod --timeout 900
gcloud run services update api-execute \
  --image us-central1-docker.pkg.dev/sudamerica-prod/sudamerica/api-execute:latest \
  --region us-central1 --project sudamerica-prod
```

### Deploy frontend

```bash
cd D:/Sudamérica.AI/MVP/MVP/frontend
gcloud builds submit --config cloudbuild-frontend.yaml --project sudamerica-prod --timeout 900
gcloud run services update frontend \
  --image us-central1-docker.pkg.dev/sudamerica-prod/sudamerica/frontend:latest \
  --region us-central1 --project sudamerica-prod
```

### Migracion manual en Cloud SQL

```python
import psycopg2
conn = psycopg2.connect(
    host='34.133.88.146', port=5432,
    user='postgres', password='SET_VIA_SECRET_MANAGER', database='sudamerica',
)
conn.autocommit = True
cur = conn.cursor()
cur.execute(open('backend/infra/017_menu_imports.sql').read())
```

### Verificar import history de un tenant

```sql
SELECT version, source_type, filename, items_confirmed, status, set_as_official, created_at
FROM menu_imports
WHERE tenant_id = '<uuid>'
ORDER BY version DESC LIMIT 10;
```

### Forzar regenerar PDF auto

Actualizar `agente_config.menu_pdf_url = NULL` para un tenant → en el proximo pedido de menu via WhatsApp, `_auto_generate_menu_pdf()` regenera desde productos y la sube a `tenants/{tid}/media/document/menu-auto.pdf`.

---

## 11. Pendientes y mejoras futuras

- **Drag-to-reorder** de modifiers y productos dentro de una categoria.
- **Search/Filter UI** expuestos en la pagina `/carta` (los filtros existen en los hooks pero no tienen controles UI).
- **Deprecar** `POST /menu/import` legacy una vez validado el flow preview/confirm en todos los tenants.
- **Rollback de versiones**: usar `menu_imports` para restaurar una version anterior (hard delete + re-bulk-create).
- **Refresh de signed URLs** cuando expiran los 7 dias (hoy la app regenera en caliente al consumir).
- **Auto-decremento** de `suministros.stock_actual` al entregar una comanda basado en `recetas`.
- **Sucursal-specific pricing** via `sucursal_producto_precios` (tabla ya existe pero sin UI).

---

## 12. Referencias

- Flowchart oficial: `Docs/flujos/Carga_menu.pdf`
- Plan de producto Resto Fase 1: `Docs/02_product/sudamerica_resto.md`
- Arquitectura general: `Docs/01_architecture/microservice-repo-separation.md`
- Conversacion IA end-to-end: `Docs/01_architecture/conversation-flows.md`
- Bitacora multi-sucursal: memoria `project_multi_sucursal.md`
- Bitacora WhatsApp IA: memoria `project_whatsapp_ia_flow.md`
